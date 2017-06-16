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
import os
import unittest

import fixtures
import github

import git_pull_request as gpr


class TestRunShellCommand(unittest.TestCase):
    def test_ok(self):
        gpr._run_shell_command(["echo", "arf"])

    def test_output(self):
        output = gpr._run_shell_command(["echo", "arf"], output=True)
        self.assertEqual("arf", output)

    def test_error(self):
        self.assertRaises(
            RuntimeError,
            gpr._run_shell_command,
            ["ls", "sureitdoesnoteixst"])
        gpr._run_shell_command(["ls", "sureitdoesnoteixst"],
                               raise_on_error=False)


class TestStuff(unittest.TestCase):
    def test_get_github_user_repo_from_url(self):
        self.assertEqual(
            ("github.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "https://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("github.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "git@github.com:jd/git-pull-request.git"))
        self.assertEqual(
            ("github.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "git://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("example.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("github.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "git@github.com:jd/git-pull-request"))
        self.assertEqual(
            ("example.com", "jd", "git-pull-request"),
            gpr.get_github_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request"))


class TestGitCommand(fixtures.TestWithFixtures):
    def setUp(self):
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        os.chdir(self.tempdir)
        gpr._run_shell_command(["git", "init", "--quiet"])
        gpr._run_shell_command(["git", "remote", "add", "origin",
                                "https://github.com/jd/git-pull-request.git"])
        gpr._run_shell_command(["git", "config", "branch.master.merge",
                                "refs/heads/master"])
        gpr._run_shell_command(["git", "config", "branch.master.remote",
                                "origin"])
        gpr._run_shell_command(["git", "config", "user.name", "nobody"])
        gpr._run_shell_command(["git", "config", "user.email",
                                "nobody@example.com"])

    def test_get_remote_for_branch(self):
        self.assertEqual("origin",
                         gpr.git_get_remote_for_branch("master"))

    def test_git_remote_matching_url(self):
        self.assertEqual(
            "origin",
            gpr.git_remote_matching_url(
                "https://github.com/jd/git-pull-request.git"))

    def test_git_get_remote_branch_for_branch(self):
        self.assertEqual(
            "master",
            gpr.git_get_remote_branch_for_branch("master"))

    def test_git_get_title_and_message(self):
        gpr._run_shell_command(["git", "commit", "--allow-empty",
                                "--no-edit", "-q",
                                "-m", "Import"])
        gpr._run_shell_command(["git", "commit", "--allow-empty",
                                "--no-edit", "-q",
                                "-m", "First message"])
        gpr._run_shell_command(["git", "commit", "--allow-empty",
                                "--no-edit", "-q",
                                "-m", "Last message\n\nLong body, "
                                "but not so long\n"])

        self.assertEqual((1, "Last message", "Long body, but not so long"),
                         gpr.git_get_title_and_message("master^", "master"))

        self.assertEqual((2, "Pull request for master",
                          "Last message\nFirst message"),
                         gpr.git_get_title_and_message("master^^", "master"))


class TestMessageParsing(unittest.TestCase):
    def test_only_title(self):
        self.assertEqual(
            ("foobar", "something\nawesome"),
            gpr.parse_pr_message("foobar\nsomething\nawesome"))
        self.assertEqual(
            ("foobar", "something\nawesome\n"),
            gpr.parse_pr_message("foobar\nsomething\nawesome\n"))
        self.assertEqual(
            ("foobar", "something\nawesome\n"),
            gpr.parse_pr_message("foobar\n\nsomething\nawesome\n"))


class TestExceptionFormatting(unittest.TestCase):
    def test_issue_12(self):
        e = github.GithubException(422, {
            u'documentation_url':
            u'https://developer.github.com/v3/pulls/#create-a-pull-request',
            u'message':
            u'Validation Failed',
            u'errors': [{
                u'message': u'No commits between issues-221 and issues-221',
                u'code': u'custom',
                u'resource': u'PullRequest'}
            ]}
        )
        self.assertEqual(
            "Unable to create pull request: Validation Failed (422)\n"
            "No commits between issues-221 and issues-221\n"
            "Check "
            "https://developer.github.com/v3/pulls/#create-a-pull-request "
            "for more information.",
            gpr._format_github_exception("create pull request", e))
