import os
import github
import sys
import glob


from loguru import logger

from git_pull_request.git import _run_shell_command
from git_pull_request.pagure import Client

class Github:
    
    def get_pull_request_template(self):
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

    def download_pull_request(self, g, repo, target_remote, pull_number, setup_remote): # refactory
        pull = repo.get_pull(pull_number)
        if setup_remote:
            local_branch_name = pull.head.ref
        else:
            local_branch_name = "pull/%d-%s-%s" % (
                pull.number,
                pull.user.login,
                pull.head.ref,
            )
        target_ref = "pull/%d/head" % pull.number

        _run_shell_command(["git", "fetch", target_remote, target_ref])
        try:
            _run_shell_command(["git", "checkout", local_branch_name], output=True)
        except RuntimeError:
            _run_shell_command(["git", "checkout", "-b", local_branch_name, "FETCH_HEAD"])
        else:
            _run_shell_command(["git", "reset", "--hard", "FETCH_HEAD"])

        if setup_remote:
            remote_name = "github-%s" % pull.user.login
            remote = self.get_remote_url(remote_name, raise_on_error=False)
            if not remote:
                _run_shell_command(
                    ["git", "remote", "add", remote_name, pull.head.repo.clone_url]
                )
            _run_shell_command(["git", "fetch", remote_name])
            _run_shell_command(
                ["git", "branch", "-u", "origin/%s" % pull.base.ref, local_branch_name]
            )



    def fork_and_push_pull_request(
        self,
        g,
        hosttype,
        repo_to_fork,
        rebase,
        target_remote,
        target_branch,
        branch,
        user,
        title,
        message,
        keep_message,
        comment,
        fork,
        setup_only,
        branch_prefix,
        dry_run=False,
        labels=None,
        ):

        g_user = g.get_user()

        forked = False
        if fork in ["always", "auto"]:
            try:
                repo_forked = g_user.create_fork(repo_to_fork)
            except github.GithubException as e:
                if (
                    fork == "auto"
                    and e.status == 403
                    and "forking is disabled" in e.data["message"]
                ):
                    forked = False
                    logger.info(
                        "Forking is disabled on target repository, " "using base repository"
                    )
                else:
                    logger.error(
                        "Forking is disabled on target repository, " "can't fork",
                        exc_info=True,
                    )
                    sys.exit(1)
            else:
                forked = True
                logger.info("Forked repository: %s", repo_forked.html_url)
                forked_repo_id = get_repository_id_from_url(repo_forked.clone_url)

        if branch_prefix is None and not forked:
            branch_prefix = g_user.login

        if branch_prefix:
            remote_branch = "{}/{}".format(branch_prefix, branch)
        else:
            remote_branch = branch

        if forked:
            remote_to_push = git_remote_matching_url(repo_forked.clone_url)

            if remote_to_push:
                logger.debug(
                    "Found forked repository already in remote as `%s'", remote_to_push
                )
            else:
                remote_to_push = hosttype
                _run_shell_command(
                    ["git", "remote", "add", remote_to_push, repo_forked.clone_url]
                )
                logger.info("Added forked repository as remote `%s'", remote_to_push)
            head = "{}:{}".format(forked_repo_id.user, branch)
        else:
            remote_to_push = target_remote
            head = "{}:{}".format(repo_to_fork.owner.login, remote_branch)

        if setup_only:
            logger.info("Fetch existing branches of remote `%s`", remote_to_push)
            _run_shell_command(["git", "fetch", remote_to_push])
            return

        if rebase:
            _run_shell_command(["git", "remote", "update", target_remote])

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



    def git_pull_request(
        self,
        target_remote=None,
        target_branch=None,
        title=None,
        message=None,
        keep_message=None,
        comment=None,
        rebase=True,
        download=None,
        download_setup=False,
        fork=True,
        setup_only=False,
        branch_prefix=None,
        labels=None,
    ):
        branch = self.get_branch_name()
        if not branch:
            logger.critical("Unable to find current branch")
            return 10

        logger.debug("Local branch name is `%s'", branch)

        target_branch = target_branch or self.get_remote_branch_for_branch(branch)

        if not target_branch:
            target_branch = "master"
            logger.info(
                "No target branch configured for local branch `%s', using `%s'.\n"
                "Use the --target-branch option to override.",
                branch,
                target_branch,
            )

        target_remote = target_remote or self.et_remote_for_branch(target_branch)
        if not target_remote:
            logger.critical(
                "Unable to find target remote for target branch `%s'", target_branch
            )
            return 20

        logger.debug("Target remote for branch `%s' is `%s'", target_branch, target_remote)

        target_url = self.remote_url(target_remote)
        if not target_url:
            logger.critical("Unable to find remote URL for remote `%s'", target_remote)
            return 30

        logger.debug("Remote URL for remote `%s' is `%s'", target_remote, target_url)

        hosttype, hostname, user_to_fork, reponame_to_fork = attr.astuple(
            self.repository_id_from_url(target_url)
        )
        logger.debug(
            "%s user and repository to fork: %s/%s on %s",
            hosttype.capitalize(),
            user_to_fork,
            reponame_to_fork,
            hostname,
        )

        user, password = self.get_login_password(host=hostname)
        if not user and not password:
            logger.critical(
                "Unable to find your credentials for %s.\n"
                "Make sure you have a git credential working.",
                hostname,
            )
            return 35

        logger.debug("Found %s user: `%s' password: <redacted>", hostname, user)

        if hosttype == "pagure":
            g = pagure.Client(hostname, user, password, reponame_to_fork)
            repo = g.get_repo(reponame_to_fork)
        else:
            kwargs = {}
            if hostname != "github.com":
                kwargs["base_url"] = "https://" + hostname + "/api/v3"
                logger.debug("Using API base url `%s'", kwargs["base_url"])
            g = github.Github(user, password, **kwargs)
            repo = g.get_user(user_to_fork).get_repo(reponame_to_fork)

        if download is not None:
            retcode = self.download_pull_request(
                g, repo, target_remote, download, download_setup
            )

        else:
            retcode = self.fork_and_push_pull_request(
                g,
                hosttype,
                repo,
                rebase,
                target_remote,
                target_branch,
                branch,
                user,
                title,
                message,
                keep_message,
                comment,
                fork,
                setup_only,
                branch_prefix,
                dry_run,
                labels,
            )

        self.approve_login_password(host=hostname, user=user, password=password)

        return retcode