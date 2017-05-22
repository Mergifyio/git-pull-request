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
