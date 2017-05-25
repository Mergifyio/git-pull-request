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
            ("jd", "git-pull-request"),
            gpr.get_github_user_repo_from_url(
                "https://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("jd", "git-pull-request"),
            gpr.get_github_user_repo_from_url(
                "git@github.com:jd/git-pull-request.git"))
        self.assertEqual(
            ("jd", "git-pull-request"),
            gpr.get_github_user_repo_from_url(
                "git://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("jd", "git-pull-request"),
            gpr.get_github_user_repo_from_url(
                "https://example.com/jd/git-pull-request.git"))


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

    def test_get_title_from_git_log(self):
        self.assertEqual(
            "Pull request for master",
            gpr.get_title_from_git_log("foobar\nfoobaz", "master"))
        self.assertEqual(
            "only one commit",
            gpr.get_title_from_git_log("only one commit", "master"))
        self.assertEqual(
            "only one commit",
            gpr.get_title_from_git_log("only one commit\n", "master"))
