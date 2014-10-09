# -*- coding: utf-8 -*-
"""Tests for server initialization and loop logic."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core import server


def test_boot():

    """Test that we can initiate and boot the server."""

    array = []

    # noinspection PyUnusedLocal
    # This one should not fire, as init is not pre-hookable
    @server.EVENTS.hook("server_init", pre=True)
    def _init_pre_hook():
        array.append(0)

    # noinspection PyUnusedLocal
    @server.EVENTS.hook("server_init")
    def _init_post_hook_1():
        array.append(1)

    # noinspection PyUnusedLocal
    @server.EVENTS.hook("server_boot")
    def _init_post_hook_2():
        array.append(2)

    server.boot()
    assert array == [1, 2]
    assert server.SOCKETS.listening


def test_loop():

    """Test that we can loop through the server."""

    class _DummyException(Exception):
        pass

    # noinspection PyUnusedLocal
    @server.EVENTS.hook("server_loop")
    def _loop_hook():
        raise _DummyException()

    with pytest.raises(_DummyException):
        server.loop()
