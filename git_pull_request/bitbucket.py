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


def is_bitbucket(hostname):
    return requests.get("https://api.%s/2.0/repositories/" % hostname).ok


class Client:
    """Bitbucket interface loosely compatible with the github client."""

    def __init__(self, hostname, user, password, user_to_fork, reponame_to_fork):
        """Client object hold all the necessary information."""
        self.host = hostname
        self.user = user
        self.password = password

        self.user_to_fork = user_to_fork
        self.reponame_to_fork = reponame_to_fork
        self.fork_path = "repositories/%s/%s/forks" % (
            self.user_to_fork,
            self.reponame_to_fork,
        )
        self.session = requests.session()

    def create_fork(self, _):
        LOG.debug("check if the fork already exists")
        params = {"q": 'full_name="%s/%s"' % (self.user, self.reponame_to_fork)}
        forks = self.get(self.fork_path, params=params, error_ok=True)["values"]
        if not forks:
            LOG.info("requesting a fork creation")
            forks = [self.post(self.fork_path)]

        return self.get_fork_urls(forks[0])

    def create_pull(self, base, head, title, body):
        branch_from = head.split(":", 1)[1]

        endpoint = "repositories/%s/%s/pullrequests" % (
            self.user_to_fork,
            self.reponame_to_fork,
        )
        data = dict(
            description=body,
            title=title,
            source=dict(
                branch=dict(
                    name=branch_from,
                ),
                repository=dict(full_name="%s/%s" % (self.user, self.reponame_to_fork)),
            ),
        )
        resp = self.post(
            endpoint,
            data=data,
        )

        class Pull:
            html_url = "https://%s/%s/%s/pull-requests/%d" % (
                self.host,
                self.user_to_fork,
                self.reponame_to_fork,
                resp["id"],
            )

        return Pull

    def get(self, endpoint, params=None, error_ok=False):
        return self.request("GET", endpoint, params=params, error_ok=error_ok)

    def get_fork_urls(self, fork):
        self.account_id = fork.get("owner").get("account_id")
        clones = fork.get("links").get("clone")
        urls = dict()
        for clone in clones:
            urls[clone.get("name")] = clone.get("href")

        return type(
            "ForkedRepo",
            (object,),
            dict(clone_url=urls["ssh"], html_url=urls["https"]),
        )

    def get_issue(self, x):
        class Issue:
            create_comment = self.todo

        return Issue

    def get_pull(self, pull_number):
        class PullObject:
            class user:
                login = self.user

            class head:
                ref = "head"

            number = pull_number

        return PullObject

    def get_pulls(self, base, head=None):
        class Pull:
            edit = self.todo
            host = self.host
            repo = "%s/%s" % (self.user_to_fork, self.reponame_to_fork)
            body = ""

            class head:
                ref = "head"

                class user:
                    login = self.user

            def __init__(self, number, title, ref, body):
                self.html_url = "https://%s/%s/pull-requests/%d" % (
                    self.host,
                    self.repo,
                    number,
                )
                self.body = body
                self.number = number
                self.title = title
                self.head.ref = ref

        endpoint = "repositories/%s/%s/pullrequests" % (
            self.user_to_fork,
            self.reponame_to_fork,
        )
        params = {"q": 'author.account_id="%s" AND state="OPEN"' % self.account_id}
        pulls = self.get(endpoint, params=params)["values"]
        res = []
        for pull in pulls:
            body = pull["summary"]["raw"]
            ref = pull["source"]["branch"]["name"]
            res.append(Pull(pull["id"], pull["title"], ref, body))

        return res

    def get_repo(self, reponame_to_fork):
        class Repo:
            class owner:
                login = self.user

            create_pull = self.create_pull
            get_pulls = self.get_pulls
            get_pull = self.get_pull
            get_issue = self.get_issue

        return Repo

    # Shim layer to look like a github client
    def get_user(self):
        class User:
            create_fork = self.create_fork

        return User

    def post(self, endpoint, data=None):
        return self.request("POST", endpoint, json=data)

    def request(self, method, endpoint, json=None, params=None, error_ok=False):
        url = "https://api.%s/2.0/%s" % (self.host, endpoint)
        resp = self.session.request(
            method, url, json=json, auth=(self.user, self.password), params=params
        )
        if not resp.ok:
            if resp.status_code == 401:
                raise RuntimeError(resp.json().get("error"))
            if not error_ok:
                raise RuntimeError(
                    "%s %s (%s) failed (%d) %s"
                    % (method, url, json, resp.status_code, resp.text)
                )
            return False
        return resp.json()

    @staticmethod
    def todo(*args, **kwargs):
        LOG.warning("Updating title or adding comment is not implemented yet")
