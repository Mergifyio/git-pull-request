#!/usr/bin/env python
from git_pull_request.parser import main
import setuptools

setup_requires = [
    "loguru",
]

setuptools.setup(
    name = "git_auto_pull_request",
    setup_requires= setup_requires,
    se_scm_version=True,
    py_modules=['git_pull_request'],
    entry_points={
    'console_scripts': [
        'yourscript = git_pull_request.parser:main',
    ],
    },
)
