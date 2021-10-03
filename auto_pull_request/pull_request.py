


import os
import github 
import glob
from loguru import logger
from urllib import parse

from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest 

from auto_pull_request.content import PRContent
from auto_pull_request.utility import dead_for_resource, dead_for_software, check_true_value_and_logger
from auto_pull_request.git import Git 


class RepositoryID:
    """Generate host, user and repository name from url"""

    def __init__(self, url: str = ""):
        self.url = url
        parsed = parse.urlparse(url)
        if parsed.scheme == "https": # not empty scheme usually is https
            path = parsed.path.strip()[1:]
            self.host = parsed.netloc
        elif not parsed.scheme and "@" in parsed.path: # we assume that the url is the form of ssh 
            ssh, _, path = parsed.path.partition(':')
            _, _, self.host = ssh.partition("@")
        else:
           raise ValueError("Unsupported scheme {pared.scheme}")
        self.user, self.repo = path.split("/", 1)
        if self.repo.endswith(".git"):
            self.repo = self.repo[:-4]

        if not self.user or not self.repo or not self.host:
            logger.error(f"This url has a empty entity. user: {self.user}, repo:{self.repo}, host:{self.host}")
            dead_for_software() 
            
    def __eq__(self, other:object):
        """
            one excate identical example as follows: 
            >>> parse.urlparse("https://github.com/user/repo.git")
            ParseResult(scheme='https', netloc='github.com', path='/user/repo.git', params='', query='', fragment='')
            >>> parse.urlparse("git@github.com:user/repo.git")
            ParseResult(scheme='', netloc='', path='git@github.com:user/repo.git', params='', query='', fragment='')
            
            host: github.com
            user: volcengine
            repo: volc-sdk-python
        """
        if not isinstance(other, RepositoryID):
            return False
        return (
            self.host.lower() == other.host.lower()
            and self.user.lower() == other.user.lower()
            and self.repo.lower() == other.repo.lower()
        )
    
    def https_url(self):
        return "/".join(["https:/", self.host, self.user, self.repo + ".git"])

class Remote:
    """the object control github repo, corresponding local git remote config

        self.remote_branch is the local remote branch syncing with remote repository. Such as, "origin/master".
    """
    def __init__(self, git:Git, repo:RepositoryID, remote_name:str, repo_branch:str, local_branch:str, gh_repo):
        self.git = git
        self.repo = repo
        self.user = repo.user
        self.remote_name = remote_name
        self.remote_url = repo.https_url() #TODO use https or ssh url.
        self.repo_branch = repo_branch
        self.local_branch = local_branch
        self.gh_repo = gh_repo
        # TODO0 set the value int git.config
    
    @property
    def remote_branch(self):
        return "/".join([self.remote_name, self.repo_branch])

    #todo set move ?
    def set_into_git(self):
        self.git.add_remote_ulr(self.user, self.remote_url)
        
    #todo  create instance from more data?
    @classmethod
    def create_from_git(self):
        pass

    def exist_repo_branches(self, branch):
        self.branches = self.gh_repo.get_branches()
        return branch in self.branches

    def clear_local(self):
        if not self.git.clear_status():
            logger.error("Please commit local changes firstly")
            dead_for_resource()

    def pull(self):
        self.clear_local()
        if not self.exist_repo_branches(self.repo_branch):
            return

        self.git.fetch_branch(self.remote_name, self.local_branch)
        try:
            self.git.rebase(self.remote_branch, self.local_branch)
        except RuntimeError:
            logger.error(
                f"During the rebasing {self.local_branch} from {self.remote_branch}, "
                "it is likely that your change has a merge conflict. "
                "You may resolve it by `git add . ;git rebase --continue` command. "
                "Once done run `git pull-request' again. "
                "If you want to abort conflict resolution, run `git rebase --abort'."
            )
            dead_for_resource()

    def push(self, ignore_error=False):
        self.clear_local()
        self.git.push(self.remote_name, self.local_branch, self.remote_branch, ignore_error=ignore_error)
    
class Auto:
    """ 
        Main Vars:
        self.target_repo: the self.git.Repository entity of source repository. And self.target_repo.repo also set to the git remote name.
        self.fork_repo: the self.git.Repository fork entity from self.target_repo. And self.fork_repo.repo also set to the git remote fork name.
        self.target_branch: branch names of self.fork_repo and self.target corresponding self.local_branch. AKA, the remote branch. such as "master"
        self.local_branch: local branch which will be synced to remote sources, included the source repository and forked repository by push and pull-request.
        self.gh_*: the * object from Github package
        #self.pr_base_branch: the local remote branch referring self.target_branch of self.fork_repo, such as "remote/Seven/master". Yes, the basic #formula: remote/{$targe_repo}/{$target_branch}
        #self.pr_head_branch: the local remote branch referring self.target_branch of self.target_repo, such as "remote/Github/master".
    """
    def __init__(self,
        target_url="",
        target_remote="",
        target_branch="",
        fork_branch="",
        title="",
        body="",
        keep_message=None,
        comment="",
        labels=None,
        skip_editor="",
        token=""):
        self.git = Git()
        self.content = PRContent(title, body)
        self.keep_message = keep_message
        self.comment = comment
        self.labels = labels
        self.skip_editor = skip_editor
        self.token = token
        self.target_url = target_url
        self.target_remote_name = target_remote
        self.target_branch = target_branch
        self.fork_branch = fork_branch
        self.user = ""

        self.local_branch = True if not self.target_url else False # The rightness is dependent of the user.

        self._init_basic_info()
        self._init_github()
        self._init_credential()

        self.target_remote = Remote(
            git = self.git,
            repo = self.target_repo_id, 
            remote_name = self.target_remote_name, 
            repo_branch = self.target_branch, 
            local_branch=self.local_branch,
            gh_repo=self.gh_target_repo,
        )
        self.fork_remote = Remote(
            git = self.git,
            repo =  RepositoryID(self.gh_fork_repo.clone_url),
            remote_name = self.gh_user.login,
            repo_branch = self.fork_branch, #TODO costume repo_branch;...
            local_branch= self.local_branch,
            gh_repo=self.gh_fork_repo,
        )
        if self.fork_remote.repo == self.target_remote.repo:
            logger.error(f"Detect the remote target repo is the forked repository, which is {self.fork_remote.remote_url}. Please assigned --target-remote, --target-url with options.")
            dead_for_resource()
        logger.success("The Initialization completed-_^")
        
    def _init_basic_info(self):
        try:
            self.local_branch = self.git.get_branch_name()
            self.target_branch = self.target_branch or self.git.get_remote_branch_for_branch(self.local_branch) # TODO set upstream ref and remote config
            self.target_remote_name = self.target_remote_name or self.git.get_remote_for_branch(self.local_branch)
            self.target_url = self.target_url or self.git.get_remote_url(self.target_remote_name)
        except RuntimeError as e:
            logger.error(f"Initialization of basic info fails: {e}")
            dead_for_resource()
        check_true_value_and_logger(self.local_branch, "Unable find current branch", os.EX_UNAVAILABLE)
        check_true_value_and_logger(self.target_branch, "Unable find remote target branch", os.EX_UNAVAILABLE)
        check_true_value_and_logger(self.target_remote_name, "Unable find remote value", os.EX_UNAVAILABLE)
        check_true_value_and_logger(self.target_url, "Unable find remote url", os.EX_UNAVAILABLE)
        
        self.target_repo_id =RepositoryID(self.target_url)
        self.host = self.target_repo_id.host

        logger.success(f"Basic Info: Remote: {self.target_remote_name} Remote URL: {self.target_url}. "
             + f"Remote branch: {self.target_branch} Local Branch: {self.local_branch}")
        

    def _init_credential(self):
        if not self.token:
            self.token = self.git.get_login_password()
            check_true_value_and_logger(self.token, f"Unable to find your token of {self.git.host}. "
                "Make sure you have a git credential working.", os.EX_UNAVAILABLE)
        else:
            self.git.approve_login_password(host=self.host, user=self.user, password=self.token) #TODO hide debug info of the token
        logger.info(f"Found user: {self.user} password: <redacted> in host {self.git.host}")

    def _init_github(self):
        try:
            self.gh = github.Github(self.token)
        except UnknownObjectException as e:
            logger.error(self._format_github_exception("login with the token", e))
            dead_for_resource()
        try:
            self.gh_user = self.gh.get_user()
        except UnknownObjectException as e:
            logger.error(self._format_github_exception(f"get githut login user-{self.user}", e))
            dead_for_resource()
        self.user = self.gh_user.login
        
        try:
            self.gh_target_repo = self.gh.get_user(self.target_repo_id.user).get_repo(self.target_repo_id.repo)    
        except UnknownObjectException as e:
            logger.error(self._format_github_exception(f"get github target repo with user \
                {self.target_repo_id.user} and repo {self.target_repo_id.repo}", e))
            dead_for_resource()
        try:
            self.fork()
        except UnknownObjectException as e:
            logger.info(self._format_github_exception(f"fork repository {self.user}/{self.target_repo_id.repo}", e))
            dead_for_resource()

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

    def fork(self):
        """run fork() forcedly every time"""
        try:
            self.gh_fork_repo = self.gh_target_repo.create_fork()
        except GithubException as e:
            if  e.status == 403\
                and "forking is disabled" in e.data["message"]:
                logger.error("Forking is disabled on target repository.")
                dead_for_resource()
        
        assert self.gh_fork_repo and self.gh_fork_repo.clone_url, "fork repo should not empty"

        logger.success(f"Forked repository: {self.gh_fork_repo.clone_url}", )
        
    def run(self):
        self.update()
        self.sync()
        logger.info("Done~ ^_^")

    def update(self):
        self.target_remote.pull()
        self.fork_remote.pull()
        self.fork_remote.push(ignore_error=True)

    def sync(self):
        self.push_pr()

    def push_pr(self):
        self.fill_content()
        pulls = list(self.gh_target_repo.get_pulls(base=self.target_remote.repo_branch, head=self.target_remote.local_branch))
        if not pulls:
            pr = self.create_pr()
        else:
            pr = pulls[0]
            if len(pulls) > 1:
                logger.info(f"Pull-request({pulls[1:]}) has been ignored.")
            self.upgrade_pr_info(pr)

    def create_pr(self):
        try:
            pr = self.gh_target_repo.create_pull(
                base=self.target_remote.repo_branch, head=self.target_remote.local_branch, title=self.content.title, body=self.content.body
            )
        except github.GithubException as e:
            logger.error(self._format_github_exception("create pull request", e))
            dead_for_resource()
        logger.info("Pull-request created: %s", pr.html_url)
        return pr

    def fill_content(self):
        """If self.content has empty value, Get title and body summary for patches between 2 commits.
        """
        if self.content:
            return

        title = self.git.get_formated_title(self.target_remote.repo_branch, self.target_remote.local_branch)
        body = self.git.get_formated_logs(self.target_remote.repo_branch, self.target_remote.local_branch)
        if not self.skip_editor:
            edited = self.git.editor_str(str(PRContent(title, body)))
            self.content.fill_empty(PRContent(content=edited))
        else:
            self.content.reset_empty(PRContent(title, body))

    def upgrade_pr_info(self, pr:PullRequest):
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

    @staticmethod
    def _format_github_exception(action:str , e: GithubException):
        url = e.data.get("documentation_url", "GitHub documentation")
        errors_msg = "\n".join(
            error.get("message", "") for error in e.data.get("errors", {}) # type: ignore
        )
        return (
            "Unable to %s: %s (%s)\n"
            "%s\n"
            "Check %s for more information."
            % (action, e.data.get("message"), e.status, errors_msg, url)
        )

    def exist_remote_branch(self):
        pass
        # git ls-remote --exit-code --heads git@github.com:user/repo.git branch-name