==================
 git-pull-request
==================

.. image:: https://travis-ci.org/jd/git-pull-request.png?branch=master
    :target: https://travis-ci.org/jd/git-pull-request
    :alt: Build Status

.. image:: https://badge.fury.io/py/git-pull-request.svg
    :target: https://badge.fury.io/py/git-pull-request

git-pull-request is a command line tool to send GitHub pull-request from your
terminal.

Installation
============

Use the standard Python installation method::

  pip install git-pull-request


Usage
=====
You need to write your GitHub credentials into your `~/.netrc file`. In case you
have 2FA enabled, make sure to replace your password by a
`Personal access token <https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/>`_::

  machine github.com login jd password f00b4r

Note: since credentials are stored in plain text, you should encrypt your `$HOME`
directory to improve security.

Once you made a bunch of commits into a branch, just type::

  git pull-request

This will:

1. Fork the upstream repository into your account (if needed)
2. Add your forked repository as a remote named "github" (if needed)
3. Force push your current branch to your remote
4. Create a pull-request for your current branch to the remote matching branch,
   or master by default.

If you add more commits to your branch later or need to rebase your branch to
edit some commits, you will just need to run `git pull-request` to update your
pull-request. git-pull-request automatically detects that a pull-request has
been opened for your current working branch.

Workflow advice
===============
When sending pull-requests, it's preferable to do so from your own branch. You
can create your own branch from `master` by doing::

  $ git checkout -b myownbranch --track origin/master

This will checkout a new branch called `myownbranch` that is a copy of master.
Using the `--track` option makes sure that the upstream source branch is
written in your `.git/config` file. This will allow git-pull-request to know to
which branch send the pull-request.

Since this is long to type, you can use an alias in git to make it faster::

  $ git config --global alias.nb "checkout --track origin/master -b"

This will create a `git nb` alias that will create a new branch tracking master
and checking it out. You can then use it like that::

  $ git nb foobar
  Branch foobar set up to track remote branch master from origin.
  Switched to a new branch 'foobar'

Difference with hub
===================
The command-line wrapper `hub`_ provides `hub fork` and `hub pull-request` as
command line tols to fork and create pull-request for a long time now.

Unfortunately, it's hard to combine them in an automatic way to implement this
complete workflow. For example, if you need to update your pull-request,
there's no way it can know that a pull-request has already been opened and
calling `hub pull-request` would open a new pull-request.

git-pull-request wraps all those operation in a single hand convenient tool.

.. _hub: https://hub.github.com/
