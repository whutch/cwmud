#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup and distribution."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import os
from os.path import abspath, dirname
from setuptools import find_packages, setup
import sys

PROJECT_ROOT = dirname(abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from cwmud import __author__, __contact__, __homepage__, get_version


def get_reqs(path):
    """Parse a pip requirements file.

    :param str path: The path to the requirements file
    :returns list: A list of package strings

    """
    reqs = []
    with open(path) as req_file:
        for line in req_file:
            # Remove any comments
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                reqs.append(line)
    return reqs


setup(
    name="cwmud",
    version=get_version(),
    # PyPI metadata
    description="Clockwork MUD server",
    long_description=open("README.rst").read(),
    author=__author__,
    author_email=__contact__,
    url=__homepage__,
    license="MIT",
    keywords=["clockwork", "mud", "mux", "moo", "mush"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    # Packaging
    packages=find_packages(),
    zip_safe=False,
    # Requirements
    install_requires=get_reqs("requirements.txt"),
)
