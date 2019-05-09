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

import daiquiri

import requests


LOG = daiquiri.getLogger("git-pull-request")


def is_pagure(hostname):
    return requests.get("https://%s/api/0/-/version" % hostname).ok


class Client:
    """Pagure interface loosely compatible with the github client."""

    def __init__(self, hostname, user, password, reponame_to_fork):
        """Client object hold all the necessary information."""
        self.host = hostname
        self.user = user
        self.token = password
        self.reponame_to_fork = reponame_to_fork
        self.fork_path = "fork/%s/%s" % (self.user, self.reponame_to_fork)
        self.project_token = None
        self.session = requests.session()
        # Do not use netrc because it forces a Basic authorization header
        self.session.trust_env = False

    def request(self, method, endpoint, data=None, token=None, error_ok=False):
        if token is None:
            token = self.token
        url = "https://%s/api/0/%s" % (self.host, endpoint)
        resp = self.session.request(method, url, data=data, headers=dict(
            Authorization="token %s" % token))
        if not resp.ok:
            if resp.status_code == 401:
                raise RuntimeError(resp.json().get("error"))
            if not error_ok:
                raise RuntimeError("%s %s (%s) failed (%d) %s" % (
                    method, url, data, resp.status_code, resp.text))
            return False
        return resp.json()

    def get(self, endpoint, error_ok=False):
        return self.request("GET", endpoint, error_ok=error_ok)

    def post(self, endpoint, data=None, token=None):
        return self.request("POST", endpoint, data, token)

    # Main procedures
    def get_project_tokens(self):
        return self.get(
            "%s/connector" % self.fork_path)["connector"]["api_tokens"]

    def get_project_token(self):
        """Get or Create an API key for the project fork."""
        if not self.project_token:
            # Check if token already exists
            tokens = list(filter(
                lambda x: x["description"] == "git-pull-request" and
                          not x["expired"], self.get_project_tokens()))
            if tokens:
                self.project_token = tokens[0]["id"]
        if not self.project_token:
            # Otherwise, create the token
            resp = self.post("%s/token/new" % self.fork_path, dict(
                description="git-pull-request",
                acls=["pull_request_comment", "pull_request_create"]))
            self.project_token = resp["token"]["id"]
        return self.project_token

    def enable_pull_request(self, project):
        options = self.get("%s/options" % project)["settings"]
        if not options["pull_requests"]:
            LOG.debug("Enabling pull-request on %s", project)
            # TODO: update the options when
            # https://pagure.io/pagure/issue/4448 is solved, e.g.:
            # options["pull_requests"] = True
            options = {"pull_requests": True}
            self.post("%s/options/update" % project, options)

    def get_repo_urls(self, reponame):
        urls = self.get("{}/git/urls".format(reponame))["urls"]
        if "ssh" not in urls:
            raise RuntimeError("%s: ssh url is missing" % reponame)
        return type('ForkedRepo', (object,), dict(
            clone_url=urls["ssh"].format(username=self.user),
            html_url=urls["git"]))

    def create_fork(self, _):
        LOG.debug("check if the fork already exists")
        if not self.get(self.fork_path, error_ok=True):
            LOG.info("requesting a fork creation")
            # Repo can be $repo or $namespace/$repo
            repoinfo = self.reponame_to_fork.rsplit("/", 1)
            repo = repoinfo.pop()
            namespace = None
            if repoinfo:
                namespace = repoinfo.pop()
            self.post("fork",
                      {"repo": repo, "namespace": namespace, "wait": True})
        self.enable_pull_request(self.fork_path)
        return self.get_repo_urls(self.fork_path)

    def get_pulls(self, base, head):
        class Pull:
            edit = self.todo
            host = self.host
            repo = self.reponame_to_fork
            body = ""

            def __init__(self, number, title):
                self.html_url = "https://%s/%s/pull-request/%d" % (
                    self.host, self.repo, number)
                self.number = number
                self.title = title

        # Pagure head doesn't contain the username
        branch_from = head.split(":", 1)[1]
        pulls = []
        # TODO: support pagination
        for pull in filter(lambda x: (x["branch"] == base and
                                      x["branch_from"] == branch_from),
                           self.get("%s/pull-requests?author=%s" % (
                               self.reponame_to_fork, self.user))["requests"]):
            pulls.append(Pull(pull["id"], pull["title"]))
        return pulls

    def create_pull(self, base, head, title, body):
        # Pagure head doesn't contain the username
        branch_from = head.split(":", 1)[1]
        resp = self.post("%s/pull-request/new" % self.fork_path, dict(
            title=title,
            branch_to=base,
            branch_from=branch_from,
            initial_comment=body), self.get_project_token())

        class Pull:
            html_url = "https://%s/%s/pull-request/%d" % (
                self.host, self.reponame_to_fork, resp["id"])
        return Pull

    # Shim layer to look like a github client
    def get_user(self):
        class User:
            create_fork = self.create_fork
        return User

    def get_issue(self, x):
        class Issue:
            create_comment = self.todo

        return Issue

    def get_repo(self, reponame_to_fork):
        class Repo:
            class owner:
                login = self.user
            create_pull = self.create_pull
            get_pulls = self.get_pulls
            get_pull = self.get_pull
            get_issue = self.get_issue

        return Repo

    def get_pull(self, pull_number):
        class PullObject:
            class user:
                login = self.user

            class head:
                ref = "head"
            number = pull_number

        return PullObject

    @staticmethod
    def todo(*args, **kwargs):
        LOG.warning("Updating title or adding comment is not implemented yet")
