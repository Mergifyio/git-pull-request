import os
import github 
import glob
import json
from loguru import logger
from urllib import parse
from enum import Enum, auto

from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest 
from github.Repository import Repository 

from auto_pull_request.content import PRContent
from auto_pull_request.utility import dead_for_resource, dead_for_software, check_true_value_and_logger,format_github_exception
from auto_pull_request.git import Git 


class RepositoryID:
    """Generate host, user and repository name from url"""

    def __init__(self, url: str = ""):
        self._url = url
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

    @property
    def https_url(self):
        return "/".join(["https:/", self.host, self.user, self.repo + ".git"])

    @property
    def ssh_url(self):
        return "".join(["git@", self.host, ":", self.user, "/", self.repo + ".git"])

    def __str__(self):
        return str(self.__dict__)


class Remote:
    """the object control github repo, corresponding local git remote config

        self.remote_name is local remote name in git.config
        self.remote_branch is the local remote branch syncing with remote repository. Such as, "origin/master".
        self.user_branch: user for head branch of pull-request.
    """

    def __init__(self, remote_name:str="", repo_branch:str="", local_branch:str="", repo:RepositoryID=None, git:Git=None, gh_repo:Repository=None, config=True, fork=False, on_local=True,sync_merge=False):
        self._gh_repo = None 
        self._repo = None
        self.user = ""
        self.config = config
        self.fork =fork
        self.on_local=on_local
        self.sync_merge=sync_merge
        # TODO0 set the value int git.config
        self.remote_name = remote_name
        self.repo_branch = repo_branch
        self.local_branch = local_branch
        self.git = git
        # set property attr
        self.repo = repo
        self.gh_repo = gh_repo

        self.copy_option_list = ["user", "remote_name", "repo_branch", "local_branch", "git", "repo", "gh_repo"]
        
     
    @property
    def gh_repo(self):
        return self._gh_repo

    @gh_repo.setter
    def gh_repo(self, new_gh_repo:Repository):
        if not new_gh_repo or self._gh_repo:
            return

        self._gh_repo = new_gh_repo # type: ignore
        self.repo = RepositoryID(self._gh_repo.clone_url)  # type: ignore
          
    @property
    def repo(self):
        return self._repo

    @repo.setter
    def repo(self, new_repo:RepositoryID):
        if not new_repo or self.repo:
            assert self.repo == new_repo, "Errors, origin: {self.repo}  != repo_from_gh: {repo} "
            return 
        self._repo = new_repo
        self.user = self._repo.user
        self.remote_name =  self.remote_name or new_repo.user
        
        if self.config:
            self.set_into_git()

    def addRemote(self, other:"Remote"):
        
        for attr in other.__dict__:
            if attr in self.copy_option_list:
                self.__dict__[attr] =  self.__dict__[attr] or other.__dict__[attr]

    @property
    def remote_branch(self):
        return "/".join([self.remote_name, self.repo_branch])
    
    @property
    def user_branch(self):
        return ":".join([self.user, self.repo_branch])

    def check_integrity(self, name="Remote"):
        try:
            for attr in self.__dict__ :
                if not self.__dict__[attr] and attr in self.copy_option_list:
                    raise ValueError(f"During checking the integrity of {name}, "
                    f"found the {attr} is empty. May you provide relation variables in command line.")
        except ValueError as e:
            logger.error(e)
            dead_for_software()

    #todo set move ?
    def set_into_git(self):
        self.git.add_remote_ulr(self.repo.user, self.repo.ssh_url if self.fork else self.repo.https_url)
        
    #todo  create instance from git config?
    @classmethod
    def create_from_git(self):
        pass

    def exist_repo_branches(self, repo_branch:str):
        self.branches = self.gh_repo.get_branches()
        return repo_branch in self.branches

    def clear_local(self):
        if not self.git.clear_status(ignore_remote=not self.on_local):
            logger.error("Please commit local changes firstly")
            dead_for_resource()

    def pull(self):
        if not self.exist_repo_branches(self.repo_branch):
            logger.info(f"Because of missing of {self.repo.repo}/{self.repo_branch}, fetching")
    
        if self.sync_merge:
            sync = self.git.merge
            linter = ["merging", "git add .; git commit", "git merge --abort"]
        else:
            sync = self.git.rebase
            linter = ["rebasing", "git add .; git rebase -- continue", "git rebase --abort"]

        self.git.fetch_branch(self.remote_name, self.repo_branch)
        try:
            sync(self.remote_branch, self.local_branch)
        except RuntimeError:
            logger.error(
                f"During the {linter[0]} {self.local_branch} from {self.remote_branch}, "
                "it is likely that your change has a merge conflict. "
                f"You may resolve it by `{linter[1]}`"
                "Once done run `git pull-request' again. "
                f"If you want to abort conflict resolution, run `{linter[2]}`."
            )
            dead_for_resource()

    def push(self, ignore_error=False, retry=3, timeout=45):
        self.git.push(self.remote_name, self.local_branch, self.repo_branch, ignore_error=ignore_error, retry=retry, timeout=timeout)
    
    def __str__(self):
        return " ".join([item + ": \'" + str(self.__dict__[item]) + "\'"for item in self.__dict__ if item != "git"])


class Auto:
    """ 
        Main Vars:
        self.target_url: most important url to assign remote target repository. If don't provided, we will auto choose local remote from current branch.
        self.fork_remote: the Remote of fork from target repo. And self.fork_remote.repo also set to the git remote fork name.
        self.target_branch: the branch name of self.target_remote corresponding self.local_branch. AKA, the remote branch. such as "master"
        self.local_remote: local remote stores local info in git.config.
    """
    def __init__(self,
        target_url="",
        target_remote="",
        target_branch="",
        fork_branch="",
        fork_url="",
        fork_remote="",
        title="",
        body="",
        keep_message=None,
        comment="",
        labels=None,
        skip_editor="",
        token="",
        sync_merge=False,):
        self.git = Git()
        self.content = PRContent(title, body)
        self.keep_message = keep_message
        self.comment = comment
        self.labels = labels
        self.skip_editor = skip_editor
        self.token = token

        # accpet option parameters and basic info
        self.target_remote = Remote(
            git = self.git,
            repo = RepositoryID(target_url) if target_url else None, 
            remote_name = target_remote, 
            repo_branch = target_branch,
            fork=False,
            on_local=True if not target_url else False,
            sync_merge=sync_merge,
        )
        self.fork_remote = Remote(
            git = self.git,
            repo_branch = fork_branch,
            repo = RepositoryID(fork_url) if fork_url else None,
            remote_name = fork_remote,
            fork=True,
            on_local=True if not fork_url else False,
            sync_merge=sync_merge,
        )
        logger.info(f"accepted option parameters. \ntarget_remote: {self.target_remote}\nfork_remote: {self.fork_remote}\n")
        
        branch = self.git.get_branch_name()
        self.local_remote = self.get_local_remote(branch)
        if self.fork_remote.on_local and self.target_remote.on_local:
            pass
        elif self.target_remote.on_local:
            self.target_remote.addRemote(self.local_remote)
        else:
            self.fork_remote.addRemote(self.local_remote)
        self.target_remote.local_branch = branch
        self.fork_remote.local_branch = branch
        logger.info(f"accepted local paramters. \ntarget_remote: {self.target_remote} \nfork_remote: {self.fork_remote}\n")
        
        self._init_github()
        self._init_credential()
        logger.info(f"accepted remote paramters. \ntarget_remote: {self.target_remote}\nfork_remote: {self.fork_remote}\n")
        
        self.target_remote.check_integrity("target_remote")
        self.fork_remote.check_integrity("fork_remote")
        if self.fork_remote.repo == self.target_remote.repo:
            logger.error(f"Detect the remote target repo is the forked repository, which is {self.fork_remote.remote_url}. Please assigned --target-remote, --target-url with options.")
            dead_for_resource()
        logger.success("The Initialization completed-_^")

    def get_local_remote(self, branch):
        remote_name = self.git.get_remote_for_branch(branch)
        remote_url = self.git.get_remote_url(remote_name)
        return Remote(
            git = self.git,
            repo =  RepositoryID(remote_url) if remote_url else None ,
            remote_name = remote_name,
            repo_branch = self.git.get_remote_branch_for_branch(branch),
            local_branch = branch,
            config=False,
        )
        
    def _init_credential(self):
        if not self.token:
            self.username, self.token = self.git.get_login_password()
            check_true_value_and_logger(self.token, f"Unable to find your token of {self.fork_remote.repo.host}. "
                "Make sure you have a git credential working.", os.EX_UNAVAILABLE)
        else:
            self.git.approve_login_password(host=self.fork_remote.repo.host, user=self.fork_remote.repo.user, password=self.token) #TODO hide debug info of the token
        logger.info(f"Found user: {self.fork_remote.repo.user} password: <redacted> in host {self.fork_remote.repo.host}")

    def _init_github(self):
        assert self.target_remote.repo, "target repo must not empty"
        
        try:
            self.gh = github.Github(self.token)
        except UnknownObjectException as e:
            logger.error(format_github_exception("login with the token", e))
            dead_for_resource()
        try:
            self.gh_user = self.gh.get_user()
        except UnknownObjectException as e:
            logger.error(format_github_exception(f"get githut login user-{self.fork_remote.repo.user}", e))
            dead_for_resource()
        
        try:
            self.target_remote.gh_repo = self.gh.get_user(self.target_remote.repo.user).get_repo(self.target_remote.repo.repo) 
        except UnknownObjectException as e:
            logger.error(format_github_exception(f"get github target repo with user \
                {self.target_remote.repo.user}/{self.target_remote.repo.repo} ", e))
            dead_for_resource()
        try:
            self.fork()
        except UnknownObjectException as e:
            logger.info(format_github_exception(f"fork repository from {self.target_remote.repo.user}/{self.target_remote.repo.repo}", e))
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
        """run fork forcedly every time"""
        try:
            self.fork_remote.gh_repo = self.target_remote.gh_repo.create_fork()
        except GithubException as e:
            if  e.status == 403\
                and "forking is disabled" in e.data["message"]:
                logger.error("Forking is disabled on target repository.")
                dead_for_resource()
        
        assert self.fork_remote.repo and self.fork_remote.gh_repo, "fork repo should not empty"

        logger.success(f"Forked repository: {self.fork_remote.gh_repo.clone_url}", )
        
    def run(self):
        self.sync()
        self.push_pr()
        logger.info("Done~ ^_^")

    def sync(self):
        self.fork_remote.clear_local()
        self.target_remote.clear_local()
        self.target_remote.pull()
        self.fork_remote.pull()
        self.fork_remote.push(ignore_error=False)
        logger.success("Syncing remote and local repositories successes😄")
    
    def push_pr(self):
        self.fill_content()
        pulls = list(self.target_remote.gh_repo.get_pulls(base=self.target_remote.repo_branch, head=self.fork_remote.user_branch))
        if not pulls:
            pr = self.create_pr()
        else:
            pr = pulls[0]
            if len(pulls) > 1:
                logger.info(f"Pull-request({pulls[1:]}) has been ignored.")
            self.upgrade_pr_info(pr)

    def create_pr(self):
        try:
            pr = self.target_remote.gh_repo.create_pull(
                base=self.target_remote.repo_branch, head=self.fork_remote.user_branch, title=self.content.title, body=self.content.body
            )
        except github.GithubException as e:
            logger.error(format_github_exception(
                f"create pull request with base={self.target_remote.repo_branch} "
                f"and head={self.fork_remote.user_branch}", e))
            dead_for_resource()
        logger.success(f"Pull-request created: {pr.html_url}")
        return pr

    def fill_content(self):
        """If self.content has empty value, Get title and body summary for patches between 2 commits.
        """
        if self.content:
            return
        if self.target_remote.on_local:
            title = self.git.get_formated_title(self.target_remote.repo_branch, self.target_remote.local_branch)
            body = self.git.get_formated_logs(self.target_remote.repo_branch, self.target_remote.local_branch)
        else:
            title = "This the first title of pull-request "
            body = self.git.get_formated_body_from_scratch()

        if not self.skip_editor:
            edited = self.git.editor_str(str(PRContent(title, body)))
            self.content.fill_empty(PRContent(content=edited))
        else:
            self.content.fill_empty(PRContent(title, body))

    def upgrade_pr_info(self, pr:PullRequest):
        self.content.fill_empty(PRContent(pr.title, pr.body))
       
        if not self.keep_message:
            self.fill_content()
            pr.edit(title=self.content.title, body=self.content.body)
            logger.debug("Updated pull-request title and body")
            
        if self.comment:
            self.target_remote.gh_repo.get_issue(pr.number).create_comment(self.comment)
            logger.debug(f'Pull-request {pr.number} Commented: "{self.comment}"', )
        if self.labels:
            pr.add_to_labels(*self.labels)
            logger.debug(f"Pull-request {pr.number} added labels \"{self.labels}\"", )

        logger.success(f"Success to update pr in {pr.html_url}")

    class info_category(Enum):
            fork = auto()
            target = auto()
            none = auto()

    def get_local_remote_category(self, target_url, fork_url):
        if target_url and fork_url:
            return self.info_category.none
        if target_url:
            return self.info_category.fork
        return self.info_category.target