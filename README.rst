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
You need to write your GitHub credentials into your `~/.netrc file`::

  machine github.com login jd password f00b4r

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
