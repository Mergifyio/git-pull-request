import os
import github
import sys
import glob
import attr

from loguru import logger

from git_pull_request.git import _run_shell_command
from git_pull_request.git import Git, Repository
from git_pull_request import utility


class Github:

    def __init__(self,
                 git:Git,
                 target_url=None,
                 target_remote=None,
                 target_branch=None,
                 title=None,
                 message=None,
                 keep_message=None,
                 comment=None,
                 update=True,
                 branch_prefix=None,
                 labels=None,):

        self.git = git
        self.title = title,
        self.message = message,
        self.keep_message = keep_message,
        self.comment = comment,
        self.update = update,
        self.branch_prefix = branch_prefix,
        self.label = labels

        try:
            self.local_branch = self.git.get_branch_name()
            self.target_branch = target_branch or self.git.get_remote_branch_for_branch(self.local_branch)
            self.target_remote = target_remote or self.git.get_remote_for_branch(target_branch)
            self.target_url = target_url or self.git.get_remote_url(target_remote)
        except RuntimeError:
            utility.check_not_none_and_logger(self.local_branch, "Unable find current branch", os.EX_UNAVAILABLE)
            utility.check_not_none_and_logger(self.target_branch, "Unable find remote target branch", os.EX_UNAVAILABLE)
            utility.check_not_none_and_logger(self.target_remote, "Unable find remote value", os.EX_UNAVAILABLE)
            utility.check_not_none_and_logger(self.target_url, "Unable find remote url", os.EX_UNAVAILABLE)
        logger.debug(f"Basic Info: Remote: {self.target_remote} Remote URL: {self.target_url} "
             + f"Remote branch: {self.target_branch} Local Branch: {self.local_branch}")


        self.target_gh = Repository(self.target_url)
        logger.debug(f"user and repository to fork: {self.target_gh.user}/{self.target_gh.repo} on {self.target_gh.host}")

        # set user credential info
        self.user, self.password = self.git.get_login_password(host=self.host)
        if not self.user or not self.password:
            logger.critical(
                "Unable to find your credentials for %s.\n"
                "Make sure you have a git credential working.",
                self.host,
            )
            return 35

        logger.debug("Found %s user: %s password: <redacted>", self.host, self.user)

        # create py-github client
        self.g = github.Github(self.user, self.password)
        self.repo = self.g.get_user(self.user_to_fork).get_repo(self.repo_to_fork)

        if download:
            retcode = self.download_pull_request(download)
        else:
            retcode = self.fork_and_push_pull_request()

        self.git.approve_login_password(host=self.hostname, user=self.user, password=self.password)

        return retcode

    def _get_pull_request_template(self):
        filename = "PULL_REQUEST_TEMPLATE*"
        pr_template_paths = [
            filename,
            ".github/PULL_REQUEST_TEMPLATE/*.md",
            ".github/PULL_REQUEST_TEMPLATE/*.txt",
            os.path.join(".github", filename),
            os.path.join("docs", filename),
            filename.lower(),
            ".github/pull_request_template/*.md",
            ".github/pull_request_template/*.txt",
            os.path.join(".github", filename.lower()),
            os.path.join("docs", filename.lower()),
        ]
        for path in pr_template_paths:
            templates = glob.glob(path)
            for template_path in templates:
                if os.path.isfile(template_path):
                    with open(template_path) as t:
                        return t.read()

    def download_pull_request(self, pull_number):  # refactory
        raise RuntimeError("Please skip the download option.")

        pull = self.repo.get_pull(pull_number)
        if self.setup_remote:
            local_branch_name = pull.head.ref
        else:
            local_branch_name = "pull/%d-%s-%s" % (
                pull.number,
                pull.user.login,
                pull.head.ref,
            )
        target_ref = "pull/%d/head" % pull.number

        _run_shell_command(["git", "fetch", self.target_remote, target_ref])

        self.git.switch_forcedly_branch(local_branch_name)

        if self.setup_remote:
            remote_name = "github-%s" % pull.user.login
            remote = self.get_remote_url(remote_name, raise_on_error=False)
            if not remote:
                self.git.add_remote_ulr(remote_name, pull.head.repo.clone_url)
                self.git.fetch_branch(remote_name)
                self.git.set_upper_branch("origin/%s" % pull.base.ref, local_branch_name)

    def fork_and_push_pull_request(self):
        g_user = self.g.get_user()

        forked = False
        try:
            repo_forked = g_user.create_fork(self.repo_to_fork)
        except github.GithubException as e:
            if (
                e.status == 403
                and "forking is disabled" in e.data["message"]
            ):
                forked = False
                logger.info(
                    "Forking is disabled on target repository, " "using base repository"
                )
        else:
            forked = True
            logger.info("Forked repository: %s", repo_forked.html_url)
            forked_repo_id = RepositoryId(repo_forked.clone_url)

        if self.branch_prefix is None and not forked:
            branch_prefix = g_user.login

        if branch_prefix:
            remote_branch = f"{branch_prefix}/{self.target_branch}"
        else:
            remote_branch = self.target_branch

        if forked:
            remote_to_push = self.git.get_matching_remote(repo_forked.clone_url)

            if remote_to_push:
                logger.debug(
                    "Found forked repository already in remote as `%s'", remote_to_push
                )
            else:
                remote_to_push = self.hosttype
                self.git.add_remote_ulr(remote_to_push, repo_forked.clone_url)
                logger.info("Added forked repository as remote %s : %s", remote_to_push, repo_forked.clone_url)
            head = f"{forked_repo_id.user}:{self.branch}"  # target branch  ? TODO
        else:
            remote_to_push = self.target_remote
            head = f"{self.repo_to_fork.owner.login}:{remote_branch}"

        if self.update:
            self.git.fetch_branch()
            _run_shell_command(["git", "remote", "update", self.target_remote])

            logger.info(
                "Rebasing branch `%s' on branch `%s/%s'",
                branch,
                target_remote,
                target_branch,
            )
            try:
                _run_shell_command(
                    [
                        "git",
                        "rebase",
                        "remotes/%s/%s" % (target_remote, target_branch),
                        branch,
                    ]
                )
            except RuntimeError:
                logger.error(
                    "It is likely that your change has a merge conflict.\n"
                    "You may resolve it in the working tree now as described "
                    "above.\n"
                    "Once done run `git pull-request' again.\n\n"
                    "If you want to abort conflict resolution, run "
                    "`git rebase --abort'.\n\n"
                    "Alternatively run `git pull-request -R' to upload the change "
                    "without rebase.\n"
                    "However the change won't able to merge until the conflict is "
                    "resolved."
                )
                return 37

        pulls = list(repo_to_fork.get_pulls(base=target_branch, head=head))

        nb_commits, git_title, git_message = git_get_title_and_message(
            "%s/%s" % (target_remote, target_branch), branch
        )

        if pulls:
            for pull in pulls:
                if title is None:
                    # If there's only one commit, it's very likely the new PR title
                    # should be the actual current title. Otherwise, it's unlikely
                    # the title we autogenerate is going to be better than one
                    # might be in place now, so keep it.
                    if nb_commits == 1:
                        ptitle = git_title
                    else:
                        ptitle = pull.title
                else:
                    ptitle = title

                if keep_message:
                    ptitle = pull.title
                    body = pull.body
                else:
                    body = textparse.concat_with_ignore_marker(
                        message or git_message,
                        ">\n> Current pull request content:\n"
                        + pull.title
                        + "\n\n"
                        + pull.body,
                    )

                    ptitle, body = edit_title_and_message(ptitle, body)

                if ptitle is None:
                    logger.critical("Pull-request message is empty, aborting")
                    return 40

                if ptitle == pull.title and body == pull.body:
                    logger.debug("Pull-request title and body is already up to date")
                elif ptitle and body:
                    pull.edit(title=ptitle, body=body)
                    logger.debug("Updated pull-request title and body")
                elif ptitle:
                    pull.edit(title=ptitle)
                    logger.debug("Updated pull-request title")
                elif body:
                    pull.edit(body=body)
                    logger.debug("Updated pull-request body")

                if comment:
                    # FIXME(jd) we should be able to comment directly on a PR
                    # without getting it as an issue but pygithub does not
                    # allow that yet
                    repo_to_fork.get_issue(pull.number).create_comment(comment)
                    logger.debug('Commented: "%s"', comment)

                if labels:
                    logåger.debug("Adding labels %s", labels)
                    pull.add_to_labels(*labels)

                logger.info("Pull-request updated: %s", pull.html_url)
        else:
            # Create a pull request
            if not title or not message:
                title = title or git_title
                message = message or git_message
                title, message = edit_title_and_message(title, message)

            if title is None:
                logger.critical("Pull-request message is empty, aborting")
                return 40å

            try:
                pull = repo_to_fork.create_pull(
                    base=target_branch, head=head, title=title, body=message
                )
            except github.GithubException as e:
                logger.critical(_format_github_exception("create pull request", e))
                return 50
            else:
                logger.info("Pull-request created: %s", pull.html_url)

            if labels:
                logger.debug("Adding labels %s", labels)
                pull.add_to_labels(*labels)

    def _format_github_exception(action, exc):
        url = exc.data.get("documentation_url", "GitHub documentation")
        errors_msg = "\n".join(
            error.get("message", "") for error in exc.data.get("errors", [])
        )
        return (
            "Unable to %s: %s (%s)\n"
            "%s\n"
            "Check %s for more information."
            % (action, exc.data.get("message"), exc.status, errors_msg, url)
        )
