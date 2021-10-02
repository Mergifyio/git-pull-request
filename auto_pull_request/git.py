
import os
import re
import subprocess
import tempfile

from loguru import logger


SHORT_HASH_LEN = 5


def _run_shell_command(cmd: list[str], input: str =None, raise_on_error: bool=True) -> str:
    logger.debug(f"running '{cmd}' with input of '{input}'")
    
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
    
    def __init__(self, protocol:str="https", host:str="github.com"):
        self.username = None
        self.password = None
        self.protocol = protocol
        self.host = host

        self.conf = self.git_conf()
        self.commit_format = {
            "log": "Date:%ci; Author: %an; Commit: %h %n %s%n", 
            "markdown": "## Date:%ci; Author: %an; Commit: %h %n %s%n"
        }
    
    class git_conf:
        
        def get_pr_config(self, pr_subfix, default=None):
            self.get_config("git-pull-request." + pr_subfix, default=default)

        def get_config(self, config_name, default=""):
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
            remote_id = self.fork_repository_id_from_url(remote_url)
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
        return self.conf.get_config("branch." + branch + ".remote")


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
            
    def run_editor(self, filename)-> str:
        editor = _run_shell_command(["git", "var", "GIT_EDITOR"])
        if not editor:
            logger.warning(
                "$EDITOR is unset, you will not be able to edit the pull-request body"
            )
            editor = "cat"
        status = os.system(editor + " " + filename)
        if status != 0:
            raise RuntimeError(f"Editor({editor}) exited with status code {status}" )
        with open(filename, "r") as body:
            return body.read().strip()
      
    def editor_str(self, body: str = ""):
        with tempfile.TemporaryFile() as temp_fp:
            temp_fp.write(body.encode(encoding="utf-8"))
            return self.run_editor(temp_fp.name)
        

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
    
    def add_remote_ulr(self, remote, url):
        try:
            _run_shell_command(["git", "remote", "add", remote, url])
        except RuntimeError as e:
            url = _run_shell_command(["git", "remote", "get-url", remote])
            logger.info(f"The config has been add. The the url of {remote} remote is {url}. Exception:{e}")
    
    def fetch_branch(self, repo, branch):
        return _run_shell_command(["git", "fetch", repo, branch])
    

    def set_upper_branch(self, remote_branch, local_branch):
        return _run_shell_command(
        ["git", "branch", "-u", remote_branch, local_branch])

    def rebase(self, upstream=None, branch=None):
        if not upstream and branch:
            raise ValueError("If branch isn't empty, fill upstream firstly.") 
        return _run_shell_command(
            ["git", "rebase", upstream, branch]
        )
        
    def push(self, remote, source_branch, target_branch, set_upstream=False):
        flag = "-u" if set_upstream else ""
        return _run_shell_command(
            ["git", "push", flag, remote, f"{source_branch}:{target_branch}"])
            
