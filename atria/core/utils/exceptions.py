# -*- coding: utf-8 -*-
"""Utility exception classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)


class AlreadyExists(Exception):

    """Exception for adding an item to a collection its already in."""

    def __init__(self, key, old, new=None):
        self.key = key
        self.old = old
        self.new = new


class ServerShutdown(Exception):

    """Exception to signal that the server should be shutdown."""

    def __init__(self, forced=True):
        self.forced = forced


class ServerReboot(Exception):

    """Exception to signal that the server should be rebooted."""

    pass
