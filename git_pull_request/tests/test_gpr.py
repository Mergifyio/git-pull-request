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

import github


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


class BaseTestGitRepo(fixtures.TestWithFixtures):
    def setUp(self):
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        os.chdir(self.tempdir)
        gpr._run_shell_command(["git", "init", "--quiet"])
        gpr.git_set_config_hosttype("github")


class TestStuff(BaseTestGitRepo):
    def test_get_hosttype_user_repo_from_url(self):
        self.assertEqual(
            ("github", "github.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("github", "github.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "git@github.com:jd/git-pull-request.git"))
        self.assertEqual(
            ("github", "github.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "git://github.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("github", "example.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request.git"))
        self.assertEqual(
            ("github", "github.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "git@github.com:jd/git-pull-request"))
        self.assertEqual(
            ("github", "example.com", "jd", "git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request"))
        gpr.git_set_config_hosttype("pagure")
        self.assertEqual(
            ("pagure", "pagure.io", None, "pagure"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://pagure.io/pagure"))
        self.assertEqual(
            ("pagure", "src.fedoraproject.org", None, "rpms/git-pull-request"),
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://src.fedoraproject.org/rpms/git-pull-request"))


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


class TestGithubPRTemplate(fixtures.TestWithFixtures):
    def setUp(self):
        self.useFixture(fixtures.EnvironmentVariable("EDITOR", "cat"))
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        os.chdir(self.tempdir)

    def test_git_get_title_and_message(self):
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

        with open(os.path.join(
                  self.tempdir,
                  "PULL_REQUEST_TEMPLATE.md"), "w+") as pr_template:
            pr_template.write("# test")

        self.assertEqual((1, "Last message", "# test"),
                         gpr.git_get_title_and_message("master^", "master"))

        self.assertEqual((2, "Pull request for master", "# test"),
                         gpr.git_get_title_and_message("master^^", "master"))


class TestMessageParsing(fixtures.TestWithFixtures):
    def test_only_title(self):
        self.useFixture(fixtures.EnvironmentVariable("EDITOR", "cat"))
        tempdir = self.useFixture(fixtures.TempDir()).path
        os.chdir(tempdir)
        self.assertEqual(
            ("foobar", "something\nawesome"),
            gpr.parse_pr_message("foobar\nsomething\nawesome"))
        self.assertEqual(
            ("foobar", "something\nawesome\n"),
            gpr.parse_pr_message("foobar\nsomething\nawesome\n"))
        self.assertEqual(
            ("foobar", "something\nawesome\n"),
            gpr.parse_pr_message("foobar\n\nsomething\nawesome\n"))


class TestMessageEditor(fixtures.TestWithFixtures):
    def setUp(self):
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        os.chdir(self.tempdir)
        self.useFixture(fixtures.EnvironmentVariable("EDITOR", "cat"))

    def test_edit_title_and_message(self):
        self.assertEqual(("foobar", "something\nawesome"),
                         gpr.edit_title_and_message(
                         "foobar", "something\nawesome"))

    def test_edit_title_and_message_failure(self):
        self.useFixture(fixtures.EnvironmentVariable("EDITOR", "false"))
        self.assertRaises(RuntimeError,
                          gpr.edit_title_and_message,
                          "foobar", "something\nawesome")


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

    def test_no_message(self):
        e = github.GithubException(422, {
            'message': 'Validation Failed',
            'documentation_url':
            'https://developer.github.com/v3/pulls/#create-a-pull-request',
            'errors': [{
                'resource': 'PullRequest',
                'field': 'head',
                'code': 'invalid'}
            ]}
        )
        self.assertEqual(
            "Unable to create pull request: Validation Failed (422)\n\n"
            "Check "
            "https://developer.github.com/v3/pulls/#create-a-pull-request "
            "for more information.",
            gpr._format_github_exception("create pull request", e))


class TestGithubHostnameUserRepoFromUrl(BaseTestGitRepo):
    def test_git_clone_url(self):
        expected = ("github", "example.com", "jd", "git-pull-request")

        self.assertEqual(
            expected,
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request"))

        self.assertEqual(
            expected,
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request.git"))

        self.assertEqual(
            expected,
            gpr.get_hosttype_hostname_user_repo_from_url(
                "https://example.com/jd/git-pull-request/"))


class TestGitConfig(fixtures.TestWithFixtures):
    def test_get_remote_for_branch(self):
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

        gpr._run_shell_command(["git", "config",
                                "git-pull-request.setup-only", "yes"])
        gpr._run_shell_command(["git", "config",
                                "git-pull-request.fork", "never"])
        gpr._run_shell_command(["git", "config",
                                "git-pull-request.target-branch",
                                "awesome_branch"])
        args = gpr.build_parser().parse_args([])
        self.assertEqual(True, args.setup_only)
        self.assertEqual("never", args.fork)
        self.assertEqual("awesome_branch", args.target_branch)
