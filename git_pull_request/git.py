
import distutils.util
import os
import re
import subprocess
import attr
import tempfile
from urllib import parse
from loguru import logger
from git_pull_request.content import PRContent



SHORT_HASH_LEN = 5

@attr.s(eq=False, hash=False)
class Repository:

    def __eq__(self, other):
        """
            one excate identical example as follows: 
            >>> parse.urlparse("https://github.com/volcengine/volc-sdk-python.git")
            ParseResult(scheme='https', netloc='github.com', path='/volcengine/volc-sdk-python.git', params='', query='', fragment='')
            >>> parse.urlparse("git@github.com:volcengine/volc-sdk-python.git")
            ParseResult(scheme='', netloc='', path='git@github.com:volcengine/volc-sdk-python.git', params='', query='', fragment='')
            
            host: github.com
            user: volcengine
            repo: volc-sdk-python.git
        """
        return (
            self.host.lower() == other.host.lower()
            and self.user.lower() == other.user.lower()
            and self.repo.lower() == other.repo.lower()
        )
    
    def __init__(self, url: str = ""):
        """Return hostype, hostname, user and repository to fork from.

 
        :param url: The URL to parse
        :return: hosttype, hostname, user, repository
        
        """
        parsed = parse.urlparse(url)
        if parsed.scheme == "https": # not empty scheme usually is https
            path = parsed.path.strip("abc")
            self.host = parsed.netloc
        elif not parsed.scheme and "@" in parsed.path: # we assume that the url is the form of ssh 
            ssh, _, path = parsed.path.partition(':')
            _, _, self.host = ssh.partition("@")
        else:
           raise ValueError("Unsupported scheme {pared.scheme}")
        self.user, self.repo = path.split("/", 1)
        if self.repo.endswith(".git"):
            self.repo = self.repo[:-4]


def _run_shell_command(cmd: list[str], input: str =None, raise_on_error: bool=True) -> str:
    logger.debug("running %s", cmd)
    
    output = subprocess.PIPE
    sub = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
        stdout=output, stderr=output, encoding="utf-8")
    try:
        out, _ = sub.communicate(input=input, timeout=30)
    except TimeoutError:
        sub.kill()
        logger.debug(f"{cmd} is killed because of TIMEOUTERROR")
        out, _ = sub.communicate(input=input, timeout=30)
    if raise_on_error and sub.returncode:
        raise RuntimeError("%s returned %d" % (cmd, sub.returncode))
    logger.debug(f"output of {cmd}: {out.strip()}")
    return out.strip()


class Git: 
    

    def __init__(self):
        self.username = None
        self.password = None
        self.protocol = "https"
        self.host = "github.com"

        self.conf = self.git_conf()
        self.commit_format = {
            "log": "Date:%ci; Author: %an; Commit: %h %n %s%n", 
            "markdown": "## Date:%ci; Author: %an; Commit: %h %n %s%n"
        }
    
    class git_conf:
        
        def get_pr_config(self, pr_subfix, default=None):
            self.get_config("git-pull-request." + pr_subfix, default=default)

        def get_config(self, config_name, default=None):
            if hasattr(self, config_name):
                return getattr(self, config_name)
            try:
                command_list = ["git", "config", "--get", config_name]
                setattr(self, config_name, _run_shell_command(command_list))    
                return getattr(self, config_name)  
            except RuntimeError:
                logger.debug(f"get_config: run command fail: {command_list}.")
                return default

        def set_pr_config(self, pr_subfix, value):
            self.set_config("git-pull-request." + pr_subfix, value)
            
        def set_config(self, config_name, value):
            _run_shell_command(["git", "config", config_name, value])
            
    def get_login_password(self):
        """Get login/password from git credential."""
        if self.username and self.password:
            return self.username, self.password

        request = "protocol={}\nhost={}\n".format(self.protocol, self.host).encode()

        out = _run_shell_command(["git", "credential", "fill"], input=request)
        for line in out.split("\n"):
            key, _, value = line.partition("=")
            if key == "username":
                self.username = value.decode()
            elif key == "password":
                self.password = value.decode()
            if self.username and self.password:
                return self.username, self.password

    def approve_login_password(self, user, password, host="github.com", protocol="https"):
        """Tell git to approve the credential."""
        request = f"protocol={protocol}\nhost={host}\nusername={user}\npassword={password}\n"
        output = _run_shell_command(request)
        logger.info(f"git credential status:{output}")

    def get_matching_remote(self, wanted_url):
        wanted_id = self.get_repository_id_from_url(wanted_url)

        remotes = _run_shell_command(["git", "remote", "-v"])
        for remote in remotes:
            name, remote_url, push_pull = re.split(r"\s", remote)
            if push_pull != "(push)":
                continue
            remote_id = self.repository_id_from_url(remote_url)
            if wanted_id == remote_id:
                return name


    def get_remote_url(self, remote="origin"):
        return self.conf.get_config("remote." + remote + ".url" )

    def get_pr_config_hosttype(self):
        return self.conf.get_pr_config("hosttype")

    def set_pr_config_hosttype(self, hosttype):
        self.conf.set_pr_config("hosttype", hosttype)


    def get_branch_name(self):
        branch = _run_shell_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if branch.upper() == "HEAD":
            raise RuntimeError("Unable to determine current branch")
        return branch

    def get_remote_url_for_branch(self, branch):
        return self.conf.get_config("branch" + branch + ".remote")


    def get_remote_branch_for_branch(self, branch):
        branch = self.conf.get_config("branch." + branch + ".merge")
        if branch.startswith("refs/heads/"):
            return branch[11:]
        return branch

    def get_remote_for_branch(self, branch):
        return self.conf.get_config("branch." + branch + ".remote")

    def get_commit_body(self, commit):
        return _run_shell_command(["git", "show", "--format=%b", commit, "--"])

    def get_commit_titles(self, begin, end):
        return _run_shell_command(
            ["git", "log", "--no-merges", "--format=%s", "%s..%s" % (begin, end)])

    def get_formated_logs(self, begin, end):
        return _run_shell_command(
            [
                "git",
                "log",
                "--no-merges",
                "--format=" + self.commit_format,
                "%s..%s" % (begin, end),
            ])

    def get_title_and_message(self, begin, end, title=None):
        """Get title and message summary for patches between 2 commits.

        :param begin: the commits in (begin, end] will be looked up.
            commit hash of begin is ancestor of end.
        :param end: 
        :return: title, message
        """
        title = "Pull request for commit after commit \
        {begin[:SHORT_HASH_LEN]} and before {end[:SHORT_HASH_LEN]}"
        message = self.get_formated_logs(end)
        return title, message

    def run_editor(self, filename)-> str:
        editor = _run_shell_command(["git", "var", "GIT_EDITOR"])
        if not editor:
            logger.warning(
                "$EDITOR is unset, you will not be able to edit the pull-request message"
            )
            editor = "cat"
        status = os.system(editor + " " + filename)
        if status != 0:
            raise RuntimeError(f"Editor({editor}) exited with status code {status}" )
        with open(filename, "r") as body:
            content = body.read().strip()
        return content

    def edit_title_and_message(self, title, message, skip_edit: bool = False):
        if skip_edit:
            return PRContent(title, message)

        with tempfile.TemporaryFile() as temp_fp:
            temp_fp.write(title + "\n\n")
            temp_fp.write(message + "\n")
        content = self.run_editor(temp_fp.name)
        return PRContent(content=content)
        

    def switch_new_branch(self, new_branch, base_branch):
        return _run_shell_command(["git", "checkout", "-b", new_branch, base_branch])

    def switch_branch(self, branch):
        return _run_shell_command(["git", "checkout", branch])
        

    def switch_forcedly_branch(self, branch, base_branch=""):
        
        try :
            self.switch_branch(branch)
        except RuntimeError:
            if not base_branch:
                base_branch = self.get_branch_name()
            self.switch_new_branch(branch, base_branch)
        else:
            raise RuntimeError(f"Unable create new branch {branch} from branch {base_branch}")
    
    def add_remote_ulr(self, remote_branch, url):
        return  _run_shell_command(
            ["git", "remote", "add", remote_branch, url])
    
    def fetch_branch(self, repo, branch):
        return _run_shell_command(["git", "fetch", repo, branch])
    
    def set_upper_branch(self, remote_branch, local_branch):
        return _run_shell_command(
        ["git", "branch", "-u", remote_branch, local_branch])