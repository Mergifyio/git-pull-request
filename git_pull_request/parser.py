
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

import sys
import click
from loguru import logger

from git_pull_request.git import Git
from git_pull_request.github import Github


# Creates a GitHub pull-request.
@click.command("pull-request")
@click.option("--debug", prompt=True, default=False, show_default=True,
    help="If true, enable debugging.")
@click.option("--target-url" "-r", prompt=False,
    help="The remote url of branch to send a pull-request to. Default is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n" 
    "For example, you can check you target url by \"git config --get \"remote.origin.url\"\""
    )
@click.option("--target-remote" "-r", prompt=False,
    help="The remote name of the target branch to send a pull-request to. Default is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n"
    "As a example, target-remote of a cloned repository from other other people ususally is \"origin\"."
    )
@click.option("--target-branch" "-b", prompt=False,
    help="The local branch to send a pull-request to. Default current branch at local"
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n"
    )
@click.option("--title", "-t",
    help="Title of the pull request.")
@click.option("--message", "-m",
    help="Message of the pull request.")
@click.option(
    "--comment", "-C", 
    help="Comment to publish when updating the pull-request")
@click.option(
    "--plain-text",
    help="For a existing pull-request, Don't open an editor to change the pull request message.",
    )
@click.option(
    "--skip-editor",
    type=str,
    help="If not empty, use parameter of --title and --message instead of " 
    "opening edition for pull-requester content.")
@click.option("--label", "-l",
    help="The labels to add to the pull request. Can be used multiple times.")
@click.option("--branch-prefix", prompt=True, default=True, show_default=True,
    help="Prefix of the remote branch")
@click.option("--update", "-u", prompt=True, default=True, show_default=True,
    help="If false, update local change with rebasing the remote branch. Default True.")
@click.option("--user", prompt=True, type=str,
    help="The username of github to log in, which will store in \"git credential\"")
@click.option("--token", "-u", prompt=True, type=str,
    help="The personal token of github to log in, which will store in \"git credential\"."
    "If empty, we will promot in terminal to input corresponding infos.\n"
    "How to get you personal token? Please check this https://docs.github.com/en/authentication"
    "/keeping-your-account-and-data-secure/creating-a-personal-access-token")

def main(debug, target_url, target_remote, target_branch, title, message, label, branch_prefix, update, comment, skip_editor, user, token):
    if not debug:
        log_info()
    
    logger.level()
    gh = Github(
        Git(),
        target_url=target_url,
        target_remote=target_remote,
        target_branch=target_branch,
        title=title,
        message=message,
        comment=comment,
        update=update,
        branch_prefix=branch_prefix,
        labels=label,
        skip_editor=skip_editor,
        user=user,
        token=token,
        )

def log_info():
    logger.remove()
    logger.add(sys.stderr, level="INFO")