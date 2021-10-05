
import os
import re
import subprocess
import tempfile

from subprocess import TimeoutExpired
from auto_pull_request.utility import quoted_str, stop_timeout_exception
from loguru import logger


SHORT_HASH_LEN = 5
TIMEOUT_SECOND = 30

def _run_shell_command(cmd, input: str =None, raise_on_error: bool=True, timeout=TIMEOUT_SECOND, retry=1) -> str:
    assert type(cmd) == list and type(cmd[0]) == str
    new_cmd = " ".join(list(filter((lambda x: x), cmd)))
    
    logger.debug(f"running '{new_cmd}' with input of '{input}'")
    out = ""
    for _ in range(retry):
        try:
            complete = subprocess.run(
                new_cmd, 
                input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                shell=True, encoding="utf-8", timeout=timeout)
            out = complete.stdout
        except TimeoutExpired:
            logger.debug(f"{cmd} is killed because of TIMEOUTERROR. The output of ")
            raise TimeoutError
    if raise_on_error and complete.returncode:
        logger.error(f"Runned command: {complete.args}. The error output : {out}")
        raise RuntimeError("%s returned %d" % (new_cmd, complete.returncode))
    logger.debug(f"returned code of {new_cmd}: {complete.returncode}; output of that: {out}")
    return out.strip(" \t\n")

    
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
        
    def __str__(self):
        return str(self.__dict__)

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
        if  self.password:
            return self.password

        request = "protocol={}\nhost={}\n".format(self.protocol, self.host)

        out = _run_shell_command(["git", "credential", "fill"], input=request)
        for line in out.split("\n"):
            key, _, value = line.partition("=")
            if key == "username":
                self.username = value.decode()
            elif key == "password":
                self.password = value.decode()
            if self.username and self.password:
                return self.username, self.password

    def approve_login_password(self, user="", password="", host="github.com", protocol="https"):
        """Tell git to approve the credential."""
        request = f"protocol={protocol}\nhost={host}\nusername={user}\npassword={password}\n"
        output = _run_shell_command(["git", "credential", "approve"], input=request)
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
        return _run_shell_command(["git", "show", "--format=%b" , commit, "--"])

    def get_commit_titles(self, begin, end, format):
        return _run_shell_command(
            ["git", "log", "--no-merges", f"--format="+quoted_str(format), f"{begin}..{end}"])
    
    def get_formated_title(self, head1, head2):
        return  f"Pull request for commit after commit \
            {self.get_object_rsa(head1)[:SHORT_HASH_LEN]} and before {self.get_object_rsa(head2)[:SHORT_HASH_LEN]}"
    
    def get_formated_body_from_scratch(self):
        return _run_shell_command(["git", "rev-list", "HEAD", "--format="+quoted_str(self.commit_format["log"])])

    def get_object_rsa(self, obj):
        return _run_shell_command(["git", "rev-parse", obj])

    def get_formated_logs(self, begin, end):
        return _run_shell_command(
            [
                "git",
                "log",
                "--no-merges",
                "--format=" + quoted_str(self.commit_format["log"]),
                f"{begin}..{end}",
            ])
            
    def run_editor(self, filename:str)-> str:
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
      
    def editor_str(self, text: str = ""):
        with tempfile.NamedTemporaryFile() as temp_fp:
            temp_fp.write(text.encode(encoding="utf-8"))
            temp_fp.seek(0)
            _run_shell_command(cmd=["cat",temp_fp.name])
            str = self.run_editor(temp_fp.name)
            return str # explicit naming to keep tempfile alive
        

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
            out = _run_shell_command(["git", "remote", "get-url", remote], raise_on_error= True)
        except RuntimeError:
            out = ""
        else:
            _run_shell_command(["git", "remote", "remove", remote])
        out = _run_shell_command(["git", "remote", "add", remote, url])
        logger.info(f"The config has been updated. The the url of {remote} remote is {out}.")

    @stop_timeout_exception
    def fetch_branch(self, remote, branch):
        return _run_shell_command(["git", "fetch", remote, branch])
    

    def set_upper_branch(self, remote_branch, local_branch):
        return _run_shell_command(
        ["git", "branch", "-u", remote_branch, local_branch])

    def rebase(self, upstream=None, branch=None):
        if not upstream and branch:
            raise ValueError("If branch isn't empty, fill upstream firstly.") 
        return _run_shell_command(
            ["git", "rebase", upstream, branch]
        )

    @stop_timeout_exception    
    def push(self, remote, source_branch, target_branch, set_upstream=False, ignore_error=False, retry=1, timeout=45):
        flag = "-u" if set_upstream else ""
        return _run_shell_command(
            ["git", "push", "--tags", flag, remote, f"{source_branch}:{target_branch}"], raise_on_error= not ignore_error)
            
    def clear_status(self, ignore_remote=False) -> bool:
        """check the work tree wether clean
        Please run it at project root.
        """
        try:
            if (ignore_remote or not _run_shell_command(["git", "diff", "--merge-base", "HEAD", "--", "."]))\
            and not _run_shell_command(["git", "diff", "--", "."]):
                return True
        except:
            return False
        return False
    

