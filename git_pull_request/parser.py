
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

import click
import argparse
from loguru import logger

from git_pull_request.github import Github


# class DownloadAndSetupAction(argparse.Action):
#     def __call__(self, parser, namespace, values, option_strings=None):
#         setattr(namespace, "download", values)
#         if self.dest == "download":
#             setattr(namespace, "download_setup", False)
#         else:
#             setattr(namespace, "download_setup", True)

# Creates a GitHub pull-request.
@click.command("pull-request")
@click.option('-d', '--download', prompt=True, default=1, show_default=True, 
    help='A number of the pull request, which will be checkouted')
@click.option("--download-and-setup","-D", prompt=True, default=True, show_default=True,
    help='A number of the pull request, which will be checkouted. To be able to re-push it')
@click.option("--debug", prompt=True, default=False, show_default=True,
    help="If true, enable debugging.")
@click.option("--target-remote" "-n", prompt=False,
    help="Remote to send a pull-request to. Default is auto-detected from .git/config.")
@click.option("--title", "-t"
    help="Title of the pull request.")
@click.option("--message", "-m",
    help="Title of the pull request.")
@click.option("--keep-message", "-k", prompt=True, default=True, show_default=True,
    help="Don't open an editor to change the pull request message. \
        Useful when just refreshing an already-open pull request.")
@click.option("--label", "-l",
    help="The labels to add to the pull request. Can be used multiple times.")
@click.option("--branch-prefix", prompt=True, default=True, show_default=True,
    help="Prefix remote branch")
@click.option("--no-rebase", "-R", prompt=True, default=False, show_default=True,
    help="Don't rebase branch before pushing.")
@click.option(
    "--comment", "-C", 
    help="Comment to publish when updating the pull-request")
@click.option(
    "--plain-text",
    help="Don't open an editor to change the pull request message. \
        Useful when just refreshing an already-open pull request.",
    )
@click.option(
     "--fork",
    default="auto",
    type=click.Choice(["always", "never", "auto"], case_sensitive=False),
    help=(
        "Fork behavior to create the pull-request "
        "(auto: when repository can't be cloned, "
        "always: always try to fork it "
        "never: always use base repository)"
    )
)
@click.option(
    "--no-fork",
    help="Don't fork to create the pull-request")
@click.option(
    "--skip-editor",
    type=bool,
    help="If true, Don't fork to create the pull-request")
@click.option(
    "--setup-only",
    default=False,
    help="Just setup the fork repo",
)   
def main(download, download_and_setup, debug, target_remote,  title, message,  keep_message, label, branch_prefix, no_rebase, comment, plain_text, fork, setup_only, skip_editor):
    gh = Github()
    gh.git_pull_request(
        target_remote=target_remote,
        target_branch=target_branch,
        title=title,
        message=message,
        keep_message=keep_message,
        comment=comment,
        rebase=not no_rebase,
        download=download,
        download_setup=download_and_setup,
        fork=fork,
        setup_only=setup_only,
        branch_prefix=branch_prefix,
        labels=label,
        
    )


# if __name__ == "__main__":
#     sys.exit(main())
