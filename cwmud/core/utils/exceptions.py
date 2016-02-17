# -*- coding: utf-8 -*-
"""Utility exception classes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)


class AlreadyExists(Exception):

    """Exception for adding an item to a collection it is already in."""

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


class ServerReload(Exception):

    """Exception to signal that the server should be reloaded."""

    def __init__(self, new_pid=None):
        self.new_pid = new_pid
