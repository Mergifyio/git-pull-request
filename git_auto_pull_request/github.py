from click.core import F
from git_auto_pull_request.content import PRContent

import os
import github 
import glob
from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest 
from loguru import logger

from git_auto_pull_request.git import _run_shell_command
from git_auto_pull_request.git import Git, Repository
from git_auto_pull_request import utility


class Github:
    """ 
        self.target_repo: the git.Repository entity of source repository. And self.target_repo.repo also set to the git remote name.
        self.repo: the git.Repository fork entity from self.target_repo. And self.repo.repo also set to the git remote fork name.
        self.target_branch: branch names of self.repo and self.target corresponding self.local_branch. AKA, the remote branch. such as "master"
        self.local_branch: local branch which will be synced to remote sources, included the source repository and forked repository by push and pull-request.
        self.gh_*: the * object from Github package
        self.pr_base_branch: the local remote branch referring self.target_branch of self.repo, such as "remote/Seven/master". Yes, the basic formula: remote/{$targe_repo}/{$target_branch}
        self.pr_head_branch: the local remote branch referring self.target_branch of self.target_repo, such as "remote/Github/master".
    """
    def __init__(self,
                git:Git,
                target_url="",
                target_remote="",
                target_branch="",
                title="",
                body="",
                keep_message=None,
                comment="",
                labels=None,
                skip_editor="",
                token=""):
        self.git = git
        self.content = PRContent(title, body)
        self.keep_message = keep_message
        self.comment = comment
        self.labels = labels
        self.skip_editor = skip_editor
        self.token = token
        self.user = ""
        self.repo = Repository() 

        try:
            self.local_branch = self.git.get_branch_name()
            self.target_branch = target_branch or self.git.get_remote_branch_for_branch(self.local_branch) # TODO set upstream ref and remote config
            self.target_remote = target_remote or self.git.get_remote_for_branch(self.local_branch)
            self.target_url = target_url or self.git.get_remote_url(self.target_remote)
        except RuntimeError as e:
            logger.critical(f"Initialization of basic info fails: {e}")
        utility.check_true_value_and_logger(self.local_branch, "Unable find current branch", os.EX_UNAVAILABLE)
        utility.check_true_value_and_logger(self.target_branch, "Unable find remote target branch", os.EX_UNAVAILABLE)
        utility.check_true_value_and_logger(self.target_remote, "Unable find remote value", os.EX_UNAVAILABLE)
        utility.check_true_value_and_logger(self.target_url, "Unable find remote url", os.EX_UNAVAILABLE)
        logger.debug(f"Basic Info: Remote: {self.target_remote} Remote URL: {self.target_url}. "
             + f"Remote branch: {self.target_branch} Local Branch: {self.local_branch}")

        self.target_repo = Repository(self.target_url) # type: ignore
        logger.debug(f"source user and repository: {self.target_repo.user}/{self.target_repo.repo} on {self.target_repo.host}")
        self._init_repo()
        self._init_credential()
        logger.debug("Found %s user: %s password: <redacted>", self.repo.host, self.user)
        logger.info("The Initialization completed-_^")
        self.run()

    def _init_credential(self):
        if not self.user or not self.token:
            self.user, self.token = self.git.get_login_password(host=self.host)
        utility.check_true_value_and_logger(self.user, f"Unable to find your user of {self.host}. "
            "Make sure you have a git credential working.", os.EX_UNAVAILABLE)
        utility.check_true_value_and_logger(self.token, f"Unable to find your token of {self.host}. "
            "Make sure you have a git credential working.", os.EX_UNAVAILABLE)

    def _init_repo(self):
        try:
            self.gh = github.Github(self.token)
            self.gh_user = self.gh.get_user(self.user)
            self.gh_target_repo = self.gh.get_user(self.target_repo.user).get_repo(self.target_repo.repo)
            
            self.user = self.gh.get_user().login
            self.pr_base_branch = self.gh_user.login + ":" + self.local_branch
            self.pr_head_branch = self.gh_target_repo.owner.login + ":" + self.target_remote

        except UnknownObjectException as e:
            logger.critical("Initialization of  github vars fails: {e}")
        

        try:
            self.fork()
        except github.UnknownObjectException as e:
            logger.info(f"The github fork repository {self.user}/{self.repo.repo} hadn't forked: {e}")
            utility.dead_for_resource()

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

    def run(self):
        self.update()
        self.sync()
        self.git.approve_login_password(host=self.hostname, user=self.user, password=self.password)
        logger.info("Done~ ^_^")

    def fork(self):
        """run fork() forcedly every time"""
        try:
            self.gh_repo = self.gh_target_repo.create_fork()
        except GithubException as e:
            if  e.status == 403\
                and "forking is disabled" in e.data["message"]:
                logger.critical("Forking is disabled on target repository.")
                utility.dead_for_resource()
        
        logger.info(f"Forked repository: {self.gh_repo.clone_url}", )
        self.repo = Repository(self.gh_repo.clone_url)
        
        self.git.add_remote_ulr(self.repo.repo, self.gh_repo.clone_url)
        self.git.add_remote_ulr(self.target_remote, self.gh_target_repo.clone_url)
        logger.info("Added fork repository as remote %s : %s", self.repo.repo, self.gh_repo.clone_url)
        logger.info("Added fork repository as remote %s : %s", self.target_repo, self.gh_target_repo.clone_url)
        
    def update(self):
        self.git.fetch_branch(self.repo.repo, self.target_remote)
        self.git.fetch_branch(self.target_remote, self.target_remote)

        try:
            self.git.rebase(f"remotes/{self.repo.repo}/{self.target_branch}", self.local_branch)
            self.git.rebase(f"remotes/{self.target_repo}/{self.target_branch}", self.local_branch)
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

    def sync(self):
        self.git.push(self.repo.repo, self.target_branch, self.local_branch)
        self.push_pr()

    def push_pr(self):
        self.reset_content()
        pulls = list(self.gh_target_repo.get_pulls(base=self.pr_base_branch, head=self.pr_head_branch))
        if not pulls:
            pr = self.create_pr()
        else:
            pr = pulls[0]
            if len(pulls) > 1:
                logger.info(f"Pull-request({pulls[1:]}) has been ignored.")
            self.generate_pr_info(pr)

    def create_pr(self):
        try:
            pr = self.gh_target_repo.create_pull(
                base=self.pr_base_branch, head=self.pr_head_branch, title=self.content.title, body=self.content.body
            )
        except github.GithubException as e:
            logger.critical(self._format_github_exception("create pull request", e))
            utility.dead_for_resource()
        logger.info("Pull-request created: %s", pr.html_url)
        return pr

    def fill_content(self):
        """If self.content has empty value, Get title and body summary for patches between 2 commits.
        """
        if self.content:
            return
    
        title = "Pull request for commit after commit \
            {begin[:SHORT_HASH_LEN]} and before {end[:SHORT_HASH_LEN]}"
        body = self.git.get_formated_logs(self.pr_head_branch, self.local_branch)
        if not self.skip_editor:
            edited = self.git.editor_str(str(PRContent(title, body)))
            self.content.reset_empty(PRContent(content=edited))
        else:
            self.content.reset_empty(PRContent(title, body))

    def generate_pr_info(self, pr:PullRequest):
        self.content.reset_empty(PRContent(pr.title, pr.body))
       
        if not self.keep_message:
            self.fill_content()
            pr.edit(title=self.content.title, body=self.content.body)
            logger.debug("Updated pull-request title and body")
            
        if self.comment:
            self.gh_target_repo.get_issue(pr.number).create_comment(self.comment)
            logger.debug(f'Pull-request {pr.number} Commented: "%s"', self.comment)
        if self.labels:
            pr.add_to_labels(*self.labels)
            logger.debug(f"Pull-request {pr.number} added labels %s", self.labels)


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
