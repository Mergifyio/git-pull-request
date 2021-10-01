#!/usr/bin/env python
import setuptools

setup_requires = [
    "loguru==0.5.3",
    "click==8.0.1",
    "types_attrs==19.1.0",
    "attrs==21.2.0",
    "pygithub==1.55",
]

setuptools.setup(
    name = "git_auto_pull_request",
    setup_requires= setup_requires,
    use_scm_version=True,
    py_modules=['git_auto_pull_request'],
    entry_points={
    'console_scripts': [
        'parser.py = git_auto_pull_request.parser:main',
    ],
    },
    classifiers =[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
    ],
)
