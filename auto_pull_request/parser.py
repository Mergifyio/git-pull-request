
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

from os import fork
import sys
import click
from loguru import logger

from auto_pull_request.pull_request import Auto
from auto_pull_request import __version__

# Creates a GitHub pull-request.
@click.command("pull-request")
@click.option("--debug/--no-debug", default=False, show_default=True,
    help="If true, enable debugging.")
@click.option("--target-url", "-u",
    help="The remote url of branch to send a pull-request to. Default is auto-detected from .git/config. "
    "Target-url should using http or ssh as protocol."
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n" 
    "For example, you can check you target url by \"git config --get \"remote.origin.url\"\""
    )
@click.option("--target-remote", "-r",
    help="The remote name of the target repo int local git, to which we send a pull-request. Default is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n"
    "As a example, target-remote of a cloned repository from other other people ususally is \"origin\"."
    )
@click.option("--target-branch", "-b",
    help="The remote branch of target branch in local git, to which we send a pull-request. Default value is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, usually needed when you cloned from your repository, or you want "
    "to custom a pull-request.\n"
    )
@click.option("--fork-branch",
    help="The remote branch of fork repo from which we send a pull-request. Default value is auto-detected from .git/config. "
    )
@click.option("--fork-url",
    help="The remote url of fork repo from which we send a pull-request. Default value is upsteam of the current branch. "
 )
@click.option("--fork-remote",
    help="The remote name of fork repo from which we send a pull-request. Default value is upsteam name of the current branch."
 )
@click.option("--title",
    help="Title of the pull request.")
@click.option("--body",
    help="Body of the pull request.")
@click.option(
    "--comment", 
    help="Comment to publish when updating the pull-request")
@click.option(
    "--keep-message/--update-message", default=False, show_default=True,
    help="For a existing pull-request, Don't open an editor to change the pull request body.",
    )
@click.option(
    "--skip-editor/--open-editor", default=False, show_default=True,
    help="If not empty, use parameter of --title and --message instead of " 
    "opening edition for pull-requester content.")
@click.option("--labels", "-l",
    help="The labels to add to the pull request. Can be used multiple times.")
@click.option("--token", prompt=True, type=str,
    help="The personal token of github to log in, which will store in \"git credential\"."
    "If empty, we will promot in terminal to input corresponding infos.\n"
    "How to get you personal token? Please check this https://docs.github.com/en/authentication"
    "/keeping-your-account-and-data-secure/creating-a-personal-access-token")
@click.option("--sync-merge/--sync-rebase", default=False, show_default=True,
    help="Choose to the git-command to sync with remote repo. Option `--allow-unrelated-histories` with `git merge` is deafault.")
def main(debug, target_url, target_remote, target_branch, fork_branch, fork_url, fork_remote, title, body, keep_message, labels, comment, skip_editor, token, sync_merge):
    log_info(debug)
    version_lint()
    Auto(
        target_url=target_url,
        target_remote=target_remote,
        target_branch=target_branch,
        fork_branch=fork_branch,
        fork_url=fork_url,
        fork_remote=fork_remote,
        title=title,
        body=body,
        comment=comment,
        keep_message=keep_message,
        labels=labels,
        skip_editor=skip_editor,
        token=token,
        sync_merge=sync_merge,
        ).run()

def log_info(debug):
    logger.remove()
    level = "DEBUG" if debug else "SUCCESS"
    logger.add(sys.stderr, level=level)
    
def version_lint():
    logger.success(f"Auto-Pull-Request ⭐️{__version__}")