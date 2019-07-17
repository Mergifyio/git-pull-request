# -*- encoding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import distutils.util
import glob
import itertools
import logging
import operator
import os
import shutil
import subprocess
import sys
import tempfile
from urllib import parse
from uuid import uuid4

import daiquiri

from git_pull_request import pagure

import github


LOG = daiquiri.getLogger("git-pull-request")


def _run_shell_command(cmd, output=None, raise_on_error=True):
    if output is True:
        output = subprocess.PIPE

    LOG.debug("running %s", cmd)
    sub = subprocess.Popen(cmd, stdout=output, stderr=output)
    out = sub.communicate()
    if raise_on_error and sub.returncode:
        raise RuntimeError("%s returned %d" % (cmd, sub.returncode))

    if out[0] is not None:
        return out[0].strip().decode()


def get_login_password(protocol="https", host="github.com"):
    """Get login/password from git credential."""
    subp = subprocess.Popen(["git", "credential", "fill"],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    # TODO add path support
    request = "protocol={}\nhost={}\n".format(protocol, host).encode()
    username = None
    password = None
    stdout, stderr = subp.communicate(input=request)
    ret = subp.wait()
    if ret != 0:
        LOG.error("git credential returned exited with status %d", ret)
        return None, None
    for line in stdout.split(b'\n'):
        key, _, value = line.partition(b"=")
        if key == b"username":
            username = value.decode()
        elif key == b"password":
            password = value.decode()
        if username and password:
            break
    return username, password


def approve_login_password(user, password,
                           host="github.com", protocol="https"):
    """Tell git to approve the credential."""
    subp = subprocess.Popen(["git", "credential", "approve"],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    request = "protocol={}\nhost={}\nusername={}\npassword={}\n".format(
        protocol, host, user, password).encode()
    subp.communicate(input=request)
    ret = subp.wait()
    if ret != 0:
        LOG.error("git credential returned exited with status %d", ret)


def git_remote_matching_url(url):
    remotes = _run_shell_command(["git", "remote", "-v"],
                                 output=True).split('\n')
    for remote in remotes:
        if url + " (push)" in remote:
            return remote.partition("\t")[0]


def git_remote_url(remote="origin"):
    return _run_shell_command(
        ["git", "config", "--get", "remote." + remote + ".url"],
        output=True)


def git_get_config(option, default):
    out = _run_shell_command(
        ["git", "config", "--get", "git-pull-request." + option],
        output=True, raise_on_error=False)
    return out or default


def git_config_add_argument(parser, option, *args, **kwargs):
    default = kwargs.get("default")
    isboolean = kwargs.get("action") in ["store_true", "store_false"]
    if isboolean and default is None:
        default = False
    default = git_get_config(option[2:], default)
    if default:
        if isboolean:
            default = distutils.util.strtobool(default)
        kwargs["default"] = default
    return parser.add_argument(option, *args, **kwargs)


def git_get_branch_name():
    branch = _run_shell_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        output=True)
    if branch == "HEAD":
        raise RuntimeError("Unable to determine current branch")
    return branch


def git_get_remote_for_branch(branch):
    return _run_shell_command(
        ["git", "config", "--get", "branch." + branch + ".remote"],
        output=True, raise_on_error=False)


def git_get_remote_branch_for_branch(branch):
    branch = _run_shell_command(
        ["git", "config", "--get", "branch." + branch + ".merge"],
        output=True, raise_on_error=False)
    if branch.startswith("refs/heads/"):
        return branch[11:]
    return branch


def git_get_config_hosttype():
    return _run_shell_command(
        ["git", "config", "git-pull-request.hosttype"],
        output=True, raise_on_error=False)


def git_set_config_hosttype(hosttype):
    _run_shell_command(
        ["git", "config", "git-pull-request.hosttype", hosttype])


def get_hosttype(host):
    hosttype = git_get_config_hosttype()
    if hosttype == "":
        if pagure.is_pagure(host):
            hosttype = "pagure"
        else:
            hosttype = "github"
        git_set_config_hosttype(hosttype)
    return hosttype


def get_hosttype_hostname_user_repo_from_url(url):
    """Return hostype, hostname, user and repository to fork from.

    :param url: The URL to parse
    :return: hosttype, hostname, user, repository
    """
    parsed = parse.urlparse(url)
    if parsed.netloc == '':
        # Probably ssh
        host, sep, path = parsed.path.partition(":")
        if "@" in host:
            username, sep, host = host.partition("@")
    else:
        path = parsed.path[1:].rstrip('/')
        host = parsed.netloc
    hosttype = get_hosttype(host)
    if hosttype == "pagure":
        user, repo = None, path
    else:
        user, repo = path.split("/", 1)
    return hosttype, host, user, repo[:-4] if repo.endswith('.git') else repo


def split_and_remove_empty_lines(s):
    return filter(operator.truth, s.split("\n"))


def parse_pr_message(message):
    message_by_line = message.split("\n")
    if len(message) == 0:
        return None, None
    title = message_by_line[0]
    body = "\n".join(itertools.dropwhile(
        operator.not_, message_by_line[1:]))
    return title, body


def git_get_commit_body(commit):
    return _run_shell_command(
        ["git", "show", "-q", "--format=%b", commit, '--'],
        output=True)


def git_get_log_titles(begin, end):
    log = _run_shell_command(
        ["git", "log", "--format=%s", "%s..%s" % (begin, end)],
        output=True)
    return list(split_and_remove_empty_lines(log))


def git_get_title_and_message(begin, end):
    """Get title and message summary for patches between 2 commits.

    :param begin: first commit to look at
    :param end: last commit to look at
    :return: number of commits, title, message
    """
    titles = git_get_log_titles(begin, end)
    title = "Pull request for " + end
    if len(titles) == 1:
        title = titles[0]
    pr_template = find_pull_request_template()
    if pr_template:
        message = get_pr_template_message(pr_template)
    else:
        if len(titles) == 1:
            message = git_get_commit_body(end)
        else:
            message = "\n".join(titles)

    return (len(titles), title, message)


def git_pull_request(target_remote=None, target_branch=None,
                     title=None, message=None,
                     comment=None,
                     rebase=True,
                     force_editor=False,
                     download=None,
                     tag_previous_revision=False,
                     fork=True,
                     setup_only=False):
    branch = git_get_branch_name()
    if not branch:
        LOG.critical("Unable to find current branch")
        return 10

    LOG.debug("Local branch name is `%s'", branch)

    target_branch = (target_branch or
                     git_get_remote_branch_for_branch(branch))

    if not target_branch:
        target_branch = "master"
        LOG.info(
            "No target branch configured for local branch `%s', using `%s'.\n"
            "Use the --target-branch option to override.",
            branch, target_branch)

    target_remote = target_remote or git_get_remote_for_branch(target_branch)
    if not target_remote:
        LOG.critical(
            "Unable to find target remote for target branch `%s'",
            target_branch)
        return 20

    LOG.debug("Target remote for branch `%s' is `%s'",
              target_branch, target_remote)

    target_url = git_remote_url(target_remote)
    if not target_url:
        LOG.critical("Unable to find remote URL for remote `%s'",
                     target_remote)
        return 30

    LOG.debug("Remote URL for remote `%s' is `%s'", target_remote, target_url)

    hosttype, hostname, user_to_fork, reponame_to_fork = (
        get_hosttype_hostname_user_repo_from_url(target_url)
    )
    LOG.debug("%s user and repository to fork: %s/%s on %s",
              hosttype.capitalize(), user_to_fork, reponame_to_fork, hostname)

    user, password = get_login_password(host=hostname)
    if not user and not password:
        LOG.critical(
            "Unable to find your credentials for %s.\n"
            "Make sure you have a git credential working.",
            hostname,
        )
        return 35

    LOG.debug("Found %s user: `%s' password: <redacted>", hostname, user)

    if hosttype == "pagure":
        g = pagure.Client(hostname, user, password, reponame_to_fork)
        repo = g.get_repo(reponame_to_fork)
    else:
        kwargs = {}
        if hostname != "github.com":
            kwargs['base_url'] = "https://" + hostname + "/api/v3"
            LOG.debug("Using API base url `%s'", kwargs['base_url'])
        g = github.Github(user, password, **kwargs)
        repo = g.get_user(user_to_fork).get_repo(reponame_to_fork)

    if download is not None:
        download_pull_request(g, repo, target_remote, download)
    else:
        fork_and_push_pull_request(g, hosttype, repo, rebase, target_remote,
                                   target_branch, branch, user, title, message,
                                   comment,
                                   force_editor, tag_previous_revision,
                                   fork, setup_only)
    approve_login_password(host=hostname, user=user, password=password)


def download_pull_request(g, repo, target_remote, pull_number):
    pull = repo.get_pull(pull_number)
    local_branch_name = "pull/%d-%s-%s" % (pull.number, pull.user.login,
                                           pull.head.ref)
    target_ref = "pull/%d/head" % pull.number

    _run_shell_command(["git", "fetch", target_remote, target_ref])
    try:
        _run_shell_command(["git", "checkout", local_branch_name], output=True)
    except RuntimeError:
        _run_shell_command(["git", "checkout", "-b", local_branch_name,
                            "FETCH_HEAD"])
    else:
        _run_shell_command(["git", "reset", "--hard", "FETCH_HEAD"])


def edit_file_get_content_and_remove(filename):
    editor = _run_shell_command(["git", "var", "GIT_EDITOR"], output=True)
    if not editor:
        LOG.warning(
            "$EDITOR is unset, you will not be able to edit the "
            "pull-request message")
        editor = "cat"
    status = os.system(editor + " " + filename)
    if status != 0:
        raise RuntimeError("Editor exited with status code %d" % status)
    with open(filename, "r") as body:
        content = body.read().strip()
    os.unlink(filename)

    return content


def find_pull_request_template():
    filename = "PULL_REQUEST_TEMPLATE*"
    pr_template_paths = [
        filename,
        os.path.join(".github", filename),
        os.path.join("docs", filename),
    ]
    for path in pr_template_paths:
        templates = glob.glob(path)
        if templates:
            return templates[0]


def get_pr_template_message(template):
    fd, bodyfilename = tempfile.mkstemp()
    os.close(fd)
    shutil.copy(template, bodyfilename)
    content = edit_file_get_content_and_remove(bodyfilename)

    return content


def edit_title_and_message(title, message):
    fd, bodyfilename = tempfile.mkstemp()
    os.close(fd)
    with open(bodyfilename, "w") as body:
        body.write(title + "\n\n")
        body.write(message + "\n")
    content = edit_file_get_content_and_remove(bodyfilename)

    return parse_pr_message(content)


def preserve_older_revision(branch, remote_to_push):
    tag = "{}-{}".format(branch, uuid4())
    _run_shell_command(["git", "tag", tag])
    try:
        _run_shell_command(["git", "push", remote_to_push, tag])
    except RuntimeError:
        LOG.error("Unable to push tag %s for previous revision", tag)
    else:
        LOG.info("Previous revision of patchset saved on tag %s", tag)

    _run_shell_command(["git", "tag", "-d", tag])


def fork_and_push_pull_request(g, hosttype, repo_to_fork, rebase,
                               target_remote, target_branch, branch, user,
                               title, message, comment,
                               force_editor, tag_previous_revision, fork,
                               setup_only):

    g_user = g.get_user()

    forked = False
    if fork in ["always", "auto"]:
        try:
            repo_forked = g_user.create_fork(repo_to_fork)
        except github.GithubException as e:
            if (fork == "auto" and e.status == 403 and
                    "forking is disabled" in e.data["message"]):
                forked = False
                LOG.info("Forking is disabled on target repository, "
                         "using base repository")
            else:
                LOG.error("Forking is disabled on target repository, "
                          "can't fork", exc_info=True)
                sys.exit(1)
        else:
            forked = True
            LOG.info("Forked repository: %s", repo_forked.html_url)

    if forked:
        remote_to_push = git_remote_matching_url(repo_forked.clone_url)

        if remote_to_push:
            LOG.debug("Found forked repository already in remote as `%s'",
                      remote_to_push)
        else:
            remote_to_push = hosttype
            _run_shell_command(
                ["git", "remote", "add",
                 remote_to_push, repo_forked.clone_url])
            LOG.info("Added forked repository as remote `%s'", remote_to_push)
        head = "{}:{}".format(user, branch)
        remote_branch = branch
    else:
        remote_branch = "{}/{}".format(g_user.login, branch)
        remote_to_push = target_remote
        head = "{}:{}".format(repo_to_fork.owner.login, remote_branch)

    if setup_only:
        LOG.info("Fetch existing branches of remote `%s`", remote_to_push)
        _run_shell_command(["git", "fetch", remote_to_push])
        return

    if rebase:
        _run_shell_command(["git", "remote", "update", target_remote])

        LOG.info("Rebasing branch `%s' on branch `%s/%s'",
                 branch, target_remote, target_branch)
        try:
            _run_shell_command(
                ["git", "rebase",
                 "remotes/%s/%s" % (target_remote, target_branch),
                 branch])
        except RuntimeError:
            LOG.error(
                "It is likely that your change has a merge conflict.\n"
                "You may resolve it in the working tree now as described "
                "above.\n"
                "Once done run `git pull-request' again.\n\n"
                "If you want to abort conflict resolution, run "
                "`git rebase --abort'.\n\n"
                "Alternatively run `git pull-request -R' to upload the change "
                "without rebase.\n"
                "However the change won't able to merge until the conflict is "
                "resolved.")
            return 37

    LOG.info("Force-pushing branch `%s' to remote `%s/%s'",
             branch, remote_to_push, remote_branch)

    _run_shell_command([
        "git", "push", "-f",
        remote_to_push,
        "{}:{}".format(branch, remote_branch),
    ])

    pulls = list(repo_to_fork.get_pulls(base=target_branch,
                                        head=head))
    if pulls:
        for pull in pulls:
            LOG.info("Pull-request updated:\n  %s", pull.html_url)

            if force_editor:
                title, message = edit_title_and_message(title or pull.title,
                                                        message or pull.body)

            if title and message:
                pull.edit(title=title, body=message)
                LOG.debug("Updated pull-request title and message")
            elif title:
                pull.edit(title=title)
                LOG.debug("Updated pull-request title")
            elif message:
                pull.edit(body=message)
                LOG.debug("Updated pull-request message")
        if comment:
            # FIXME(jd) we should be able to comment directly on a PR without
            # getting it as an issue but pygithub does not allow that yet
            repo_to_fork.get_issue(pull.number).create_comment(comment)
            LOG.debug("Commented: \"%s\"", comment)
    else:
        # Create a pull request
        if force_editor or not (title and message):
            nb_of_commits, git_title, git_message = git_get_title_and_message(
                "%s/%s" % (target_remote, target_branch), branch)
            title = title or git_title
            message = message or git_message
            # Do not run an editor if there's only one commit or if both
            # title and message were specified
            if (force_editor or
               ((not title or not message) and nb_of_commits > 1) or
               (((title and not message) or
                 (message and not title)) and nb_of_commits == 1)):
                title, message = edit_title_and_message(title, message)

        if title is None:
            LOG.critical("Pull-request message is empty, aborting")
            return 40

        try:
            pull = repo_to_fork.create_pull(base=target_branch,
                                            head=head,
                                            title=title,
                                            body=message)
        except github.GithubException as e:
            LOG.critical(
                _format_github_exception("create pull request", e)
            )
            return 50
        else:
            LOG.info("Pull-request created: %s", pull.html_url)

    if tag_previous_revision:
        preserve_older_revision(branch, remote_to_push)


def _format_github_exception(action, exc):
    url = exc.data.get("documentation_url", "GitHub documentation")
    errors_msg = "\n".join(error.get("message", "")
                           for error in exc.data.get("errors", []))
    return (
        "Unable to %s: %s (%s)\n"
        "%s\n"
        "Check %s for more information." %
        (action, exc.data.get('message'), exc.status, errors_msg, url)
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description='Send GitHub pull-request.'
    )
    parser.add_argument("--download", "-d",
                        type=int,
                        help="Checkout a pull request")
    parser.add_argument("--debug",
                        action='store_true',
                        help="Enabled debugging.")
    git_config_add_argument(parser, "--target-remote",
                            help="Remote to send a pull-request to. "
                            "Default is auto-detected from .git/config.")
    git_config_add_argument(parser, "--target-branch",
                            help="Branch to send a pull-request to. "
                            "Default is auto-detected from .git/config.")
    parser.add_argument("--title",
                        help="Title of the pull request.")
    parser.add_argument("--message", "-m",
                        help="Message of the pull request.")
    git_config_add_argument(parser, "--no-rebase", "-R",
                            action="store_true",
                            help="Don't rebase branch before pushing.")
    git_config_add_argument(
        parser,
        "--force-editor",
        action="store_true",
        default=False,
        help="Force editor to run to edit pull-request message.")
    parser.add_argument(
        "--comment", "-C",
        help="Comment to publish when updating the pull-request"
    )
    git_config_add_argument(
        parser,
        "--tag-previous-revision",
        action="store_true",
        default=False,
        help="Preserve older revision when pushing"
    )
    group = parser.add_mutually_exclusive_group()
    git_config_add_argument(
        group,
        "--fork",
        default="auto",
        choices=["always", "never", "auto"],
        help=("Fork behavior to create the pull-request "
              "(auto: when repository can't be cloned, "
              "always: always try to fork it "
              "never: always use base repository)")
    )
    git_config_add_argument(
        group,
        "--no-fork",
        dest="fork",
        action="store_const",
        const="never",
        help="Don't fork to create the pull-request"
    )

    git_config_add_argument(
        parser,
        "--setup-only",
        action="store_true",
        default=False,
        help="Just setup the fork repo"
    )
    return parser


def main():
    args = build_parser().parse_args()

    daiquiri.setup(
        outputs=(
            daiquiri.output.Stream(
                sys.stdout,
                formatter=daiquiri.formatter.ColorFormatter(
                    fmt="%(color)s%(message)s%(color_stop)s")),),
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    try:
        return git_pull_request(
            target_remote=args.target_remote,
            target_branch=args.target_branch,
            title=args.title,
            message=args.message,
            comment=args.comment,
            rebase=not args.no_rebase,
            force_editor=args.force_editor,
            download=args.download,
            tag_previous_revision=args.tag_previous_revision,
            fork=args.fork,
            setup_only=args.setup_only
        )
    except Exception:
        LOG.error("Unable to send pull request", exc_info=True)
        return 128


if __name__ == '__main__':
    sys.exit(main())
