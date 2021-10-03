
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

from auto_pull_request.pull_request import Auto


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
    help="The remote name of the target repo to send a pull-request to. Default is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, only needed when you cloned from your repository, or you want "
    "to create a pull-request to another repository.\n"
    "As a example, target-remote of a cloned repository from other other people ususally is \"origin\"."
    )
@click.option("--target-branch", "-b",
    help="The local branch to send a pull-request to. Default value is auto-detected from .git/config. "
    "There options, target-url, target-remote and target-branch, usually needed when you cloned from your repository, or you want "
    "to custom a pull-request.\n"
    )
@click.option("--title",
    help="Title of the pull request.")
@click.option("--body",
    help="Body of the pull request.")
@click.option(
    "--comment", 
    help="Comment to publish when updating the pull-request")
@click.option(
    "--keep-message/--ignore-message", default=False, show_default=True,
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
def main(debug, target_url, target_remote, target_branch, title, body, keep_message, labels, comment, skip_editor, token):
    log_info(debug)
    Auto(
        target_url=target_url,
        target_remote=target_remote,
        target_branch=target_branch,
        title=title,
        body=body,
        comment=comment,
        keep_message=keep_message,
        labels=labels,
        skip_editor=skip_editor,
        token=token,
        ).run()

def log_info(debug):
    logger.remove()
    level = "DEBUG" if debug else "SUCCESS"
    logger.add(sys.stderr, level=level)
    