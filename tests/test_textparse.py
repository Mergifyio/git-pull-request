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
from git_pull_request import textparse


def test_ignore_marker():
    s1 = "bonjour\n"
    s2 = "hello\nthere\n"
    c = textparse.concat_with_ignore_marker(s1, s2)
    assert (
        """bonjour
> ------------------------ >8 ------------------------
> Do not modify or remove the line above.
> Everything below it will be ignored.
hello
there
"""
        == c
    )
    assert "bonjour\n" == textparse.remove_ignore_marker(c)


def test_ignore_marker_absent():
    s1 = "bonjour\n"
    assert "bonjour\n" == textparse.remove_ignore_marker(s1)
