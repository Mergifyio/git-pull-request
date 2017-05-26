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
import itertools
import logging
import netrc
import operator
import os
import subprocess
import sys
import tempfile

import daiquiri
import github
from six.moves.urllib import parse as urlparse


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


def get_login_password(site_name="github.com", netrc_file="~/.netrc"):
    """Read a .netrc file and return login/password for LWN."""
    n = netrc.netrc(os.path.expanduser(netrc_file))
    return n.hosts[site_name][0], n.hosts[site_name][2]


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


def get_github_user_repo_from_url(url):
    parsed = urlparse.urlparse(url)
    if parsed.netloc == '':
        # Probably ssh
        host, sep, path = parsed.path.partition(":")
    else:
        path = parsed.path[1:]
    user, repo = path.split("/", 1)
    return user, repo[:-4]


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


def get_title_from_git_log(log, branch):
    summary_entries = list(split_and_remove_empty_lines(log))
    if len(summary_entries) == 1:
        return summary_entries[0]
    return "Pull request for " + branch


def git_pull_request(remote=None, remote_branch=None, title=None):
    branch = git_get_branch_name()
    if not branch:
        LOG.critical("Unable to find current branch")
        return 10

    LOG.debug("Local branch name is `%s'", branch)

    remote_branch = (remote_branch or
                     git_get_remote_branch_for_branch(branch))

    if not remote_branch:
        remote_branch = "master"
        LOG.info(
            "No remote branch configured for local branch `%s', using `%s'\n"
            "Use the --remote-branch option to override.",
            branch, remote_branch)

    remote = remote or git_get_remote_for_branch(remote_branch)
    if not remote:
        LOG.critical(
            "Unable to find remote for local branch `%s'",
            remote_branch)
        return 20

    LOG.debug("Remote for branch `%s' is `%s'", branch, remote)

    remote_url = git_remote_url(remote)
    if not remote_url:
        LOG.critical("Unable to find remote URL for remote `%s'", remote)
        return 30

    LOG.debug("Remote URL for remote `%s' is `%s'", remote, remote_url)

    user_to_fork, reponame_to_fork = get_github_user_repo_from_url(remote_url)
    LOG.debug("GitHub user and repository to fork: %s/%s",
              user_to_fork, reponame_to_fork)

    try:
        user, password = get_login_password()
    except KeyError:
        LOG.critical(
            "Unable to find your GitHub crediential.\n"
            "Make sure you have a line like this in your ~/.netrc file:\n"
            "machine github.com login <login> password <pwd>"
        )
        return 35

    LOG.debug("Found GitHub user: `%s' password: <redacted>", user)

    g = github.Github(user, password)
    g_user = g.get_user()
    repo_to_fork = g.get_user(user_to_fork).get_repo(reponame_to_fork)
    repo_forked = g_user.create_fork(repo_to_fork)
    LOG.info("Forked repository: %s", repo_forked.html_url)

    remote_to_push = git_remote_matching_url(repo_forked.clone_url)

    if remote_to_push:
        LOG.debug("Found forked repository already in remote as `%s'",
                  remote_to_push)
    else:
        remote_to_push = "github"
        _run_shell_command(
            ["git", "remote", "add", remote_to_push, repo_forked.clone_url])
        LOG.info("Added forked repository as remote `%s'", remote_to_push)

    LOG.info("Force-pushing branch `%s' to remote `%s'",
             branch, remote_to_push)

    _run_shell_command(["git", "push", "-f", remote_to_push, branch])

    pulls = list(repo_to_fork.get_pulls(base=remote_branch,
                                        head=user + ":" + branch))
    if pulls:
        for pull in pulls:
            LOG.info("Pull-request already exists at: %s", pull.html_url)
            if title:
                pull.edit(title=title)
                LOG.info("Update pull-request title to: %s", title)
    else:
        # Create a pull request
        editor = os.getenv("EDITOR")
        if not editor:
            LOG.warning(
                "$EDITOR is unset, you will not be able to edit the "
                "pull-request message")
            editor = "cat"

        summary_log = _run_shell_command(
            ["git", "log",
             "--format=%s",
             remote + "/" + remote_branch + ".." + branch],
            output=True)

        title = title or get_title_from_git_log(summary_log, branch)

        fd, bodyfilename = tempfile.mkstemp()
        with open(bodyfilename, "w") as body:
            body.write(title + "\n\n")
            body.write(summary_log + "\n")
        os.system(editor + " " + bodyfilename)
        with open(bodyfilename, "r") as body:
            content = body.read().strip()
        os.unlink(bodyfilename)

        title, body = parse_pr_message(content)
        if title is None:
            LOG.critical("Pull-request message is empty, aborting")
            return 40

        pull = repo_to_fork.create_pull(base=remote_branch,
                                        head=user + ":" + branch,
                                        title=title,
                                        body=body)
        LOG.info("Pull-request created: " + pull.html_url)


def main():
    parser = argparse.ArgumentParser(
        description='Send GitHub pull-request.'
    )
    parser.add_argument("--debug",
                        action='store_true',
                        help="Enabled debugging.")
    parser.add_argument("--remote",
                        help="Remote to send a pull-request to. "
                        "Default is auto-detected from .git/config.")
    parser.add_argument("--remote-branch",
                        help="Remote branch to send a pull-request to. "
                        "Default is auto-detected from .git/config.")
    parser.add_argument("--title",
                        help="Title of the pull request.")

    args = parser.parse_args()

    daiquiri.setup(
        outputs=(
            daiquiri.output.Stream(
                sys.stdout,
                formatter=logging.Formatter(
                    fmt="%(message)s")),),
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    return git_pull_request(remote=args.remote,
                            remote_branch=args.remote_branch,
                            title=args.title)


if __name__ == '__main__':
    sys.exit(main())
