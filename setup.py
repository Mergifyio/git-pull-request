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
    version='0.1.0',
    setup_requires= setup_requires,
    use_scm_version=True,
    author="Ove",
    packages=['auto_pull_request'],
    entry_points={
    'console_scripts': [
        'auto-pull-request=auto_pull_request.parser:main',
    ],
    },
    # scripts=['auto_pull_request/parser.py'],
    classifiers =[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
    ],
)
