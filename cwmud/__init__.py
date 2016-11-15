# -*- coding: utf-8 -*-
"""A modular MUD server."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os.path import abspath, dirname

__author__ = "Will Hutcheson"
__contact__ = "will@whutch.com"
__homepage__ = "https://github.com/whutch/cwmud"
__license__ = "MIT"
__docformat__ = "restructuredtext"

VERSION = (0, 4, 0, 0, "Dapper Dan")


def get_version():
    """Return the version string."""
    return "{}{}".format(".".join([str(n) for n in VERSION[:3]]),
                         "" if VERSION[3] == 0
                         else ".dev{}".format(VERSION[3]))


def get_codename():
    """Return the codename for this version."""
    return VERSION[4]


__version__ = "{} ({})".format(get_version(), get_codename())

ROOT_DIR = dirname(dirname(abspath(__file__)))
BASE_PACKAGE = __name__
