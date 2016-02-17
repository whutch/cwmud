# -*- coding: utf-8 -*-
"""Tests for utility exception classes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from cwmud.core.utils import exceptions


def test_exception_already_exists():
    """Test that raising AlreadyExists works as intended."""
    try:
        raise exceptions.AlreadyExists("test", old=1, new=2)
    except exceptions.AlreadyExists as exc:
        assert exc.key and exc.old and exc.new


def test_exception_server_shutdown():
    """Test that raising ServerShutdown works as intended.

    The logic of what raising this does to the server is handled in server.py
    and thus tested in test_server.py, not here.

    """
    try:
        raise exceptions.ServerShutdown()
    except exceptions.ServerShutdown as exc:
        assert exc.forced is True
    try:
        raise exceptions.ServerShutdown(forced=False)
    except exceptions.ServerShutdown as exc:
        assert exc.forced is False


def test_exception_server_reboot():
    """Test that raising ServerReboot works as intended.

    The logic of what raising this does to the server is handled in server.py
    and thus tested in test_server.py, not here.

    """
    try:
        raise exceptions.ServerReboot()
    except exceptions.ServerReboot:
        pass


def test_exception_server_reload():
    """Test that raising ServerReload works as intended.

    The logic of what raising this does to the server is handled in server.py
    and __main__.py, and thus tested in test_server.py and test_main.py,
    not here.

    """
    try:
        raise exceptions.ServerReload(1)
    except exceptions.ServerReload as exc:
        assert exc.new_pid == 1
