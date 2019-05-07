# Contributing to git-pull-request

First off, thanks for taking the time to contribute!

The following as a set of guidelines for contributing to git-pull-request.
These are mostly guidelines, not rules. Use your best judgment, and fell free
to propose changes to this document in a pull request.

## Code of Conduct

This project and everyone participating in it is governed by the
[git-pull-request Code of Conduct](CODE_OF_CONDUCT.md). By participating, you
are expected to uphold this code. Please report unacceptable behavior to
[jd@mergify.io](mailto:jd@mergify.io).

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for git-pull-request.
Following these guidelines helps maintainers and the community
understand your report, reproduce the behavior, and find related reports.

Before creating bug reports, please perform a [cursory
search](https://github.com/Mergifyio/git-pull-request/issues?q=is%3Aissue%20is%3Aopen%20)
to see if the problem has already been reported. If it has and the issue is
still open, add a comment to the existing issue instead of opening a new one.
When you are creating a bug report, please [include as many details as
possbile](#how-do-i-submit-a-good-bug-report).

> **Note:** If you find a **Closed** issue that seems like it is the same thing
> that you're experiencing, open a new issue and include a link to the original
> issue in the body of your new one.

#### How Do I Submit A (Good) Bug Report?

Bugs are tracked as [GitHub
issues](https://guides.github.com/features/issues/).

Explain the problem and include additional details to help maintainers
reproduce the problem:

* **Use a clear and descriptive title** for the issue to identify the problem.

* **Describe the exact steps which reproduce the problem** in as many details
  as possible. For example, start by explaining how you use the
  git-pull-request command line, e.g. which command exactly you used in the
  terminal. When listing steps, **don't just say what you did, but explain how
  you did it**.

* **Provide specific examples to demonstrate the steps**. Include links to
  files or GitHub projects, or copy/pasteable snippets, which you use in those
  examples. If you're providing snippets in the issue, use [Markdown code
  blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).

* **Describe the behavior you observed after following the steps** and point
  out what exactly is the problem with that behavior.

* **Explain which behavior you expected to see instead and why.**


Provide more context by answering these questions:

* **Did the problem start happening recently** (e.g. after updating to a new
  version of git-pull-request) or was this always a problem?

* If the problem started happening recently, **can you reproduce the problem in
  an older version of git-pull-request?** What's the most recent version in
  which the problem doesn't happen? You can install older versions of
  git-pull-request from [the pypi
  repository](https://pypi.python.org/pypi/git-pull-request/).

* **Can you reliably reproduce the issue?** If not, provide details about how
  often the problem happens and under which conditions it normally happens.


Include details about your configuration and environment:

* **Which version of git-pull-request are you using?** You can get the exact
  version by running `pip freeze | grep "git-pull-request"` in your terminal.

* **What's the name and version of the OS you're using**?

* **What's the version of python you're using**?

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for
git-pull-request, including completely new features and minor improvements to
existing functionality. Following these guidelines helps maintainers and the
community understand your suggestion and find related suggestions.

When you are creating an enhancement suggestion, please [include as many
details as possible](#how-do-i-submit-a-good-enhancement-suggestion) and
including the steps that you imagine you would take if the feature you're
requesting existed.

#### How Do I Submit A (Good) Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub
issues](https://guides.github.com/features/issues/).

Provide the following information:

* **Use a clear and descriptive title** for the issue to identify the
  suggestion.

* **Provide a step-by-step description of the suggested enhancement** in as
  many details as possible.

* **Provide specific examples to demonstrate the steps**. Include
  copy/pasteable snippets which you use in those examples, as [Markdown code
  blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).

* **Describe the current behavior** and **explain which behavior you expected
  to see instead** and why.

* **Include screenshots and animated GIFs** which help you demonstrate the
  steps or point out the part of git-pull-request which the suggestion is
  related to. You can use [this tool](https://www.cockos.com/licecap/) to
  record GIFs on macOS and Windows, and [this
  tool](https://github.com/colinkeenan/silentcast) or [this
  tool](https://github.com/GNOME/byzanz) on Linux.

* **Explain why this enhancement would be useful** to most git-pull-request
  users.

* **List some other tools or applications where this enhancement exists.**

* **Specify which version of git-pull-request you're using.** You can get the
  exact version by running `pip freeze| grep "git-pull-request"` in your
  terminal.

* **Specify the name and version of the OS you're using.**

* **Specify the version of python you're using**

## Code Contribution

### Hacking on git-pull-request

If you're hitting a bug in git-pull-request or just want to experiment with
adding a feature, follow these steps.

#### Prerequisites

- Python >= 3.5

#### Cloning

``` command-line
$ git clone https://github.com/Mergifyio/git-pull-request
```

#### Setup your environment

From there, you can navigate into the directory where you've cloned the
git-pull-request source code, create a virtual environment and install all the
required dependencies:

``` command-line
$ cd git-pull-request
$ pip install -e .
```

#### Make your changes

``` command-line
$ git checkout -b somefeature
<edit files>
$ git commit -am 'I did some changes'
$ git pull-request
Forked repository: https://github.com/Mergifyio/git-pull-request
Force-pushing branch `somefeature' to remote `github'
Counting objects: 5, done.
Delta compression using up to 4 threads.
Compressing objects: 100% (4/4), done.
Writing objects: 100% (5/5), 562 bytes | 0 bytes/s, done.
Total 5 (delta 3), reused 0 (delta 0)
remote: Resolving deltas: 100% (3/3), completed with 3 local objects.
To https://github.com/Mergifyio/git-pull-request.git
 + 73a733f7...1be2bf29 somefeature -> somefeature (forced update)
 Pull-request created: https://github.com/git-pull-requestxyz/git-pull-request/pull/33
```

### Pull Requests

* Squash your commits.
* Include examples, outputs, etc... whenever possible.
* Include screenshots and animated GIFs in your pull request whenever possible.
