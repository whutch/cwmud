# -*- coding: utf-8 -*-
"""Tests for the server's main entry point."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from importlib import reload

import redis

import cwmud.nanny as nanny


class TestMain:

    """A collection of tests for the server's nanny process."""

    rdb = redis.StrictRedis(decode_responses=True)
    listeners = []

    @classmethod
    def setup_class(cls):
        cls.listeners = nanny.start_listeners()

    @classmethod
    def teardown_class(cls):
        for listener in cls.listeners:
            listener.terminate()

    def test_main(self):

        """Test that the nanny process runs properly."""

        channels = self.rdb.pubsub(ignore_subscribe_messages=True)

        def _server_booted(msg):
            pid = int(msg["data"])
            self.rdb.publish("server-shutdown", pid)

        channels.subscribe(**{"server-boot-complete": _server_booted})
        worker = channels.run_in_thread()
        nanny.start_nanny()
        worker.stop()
        reload(nanny)

    def test_main_reload(self):

        """Test that the nanny process can handle a reload request."""

        channels = self.rdb.pubsub(ignore_subscribe_messages=True)
        did_reload = False

        def _server_booted(msg):
            nonlocal did_reload
            pid = int(msg["data"])
            if did_reload:
                self.rdb.publish("server-shutdown", pid)
            else:
                did_reload = True
                self.rdb.publish("server-reload-request", pid)

        channels.subscribe(**{"server-boot-complete": _server_booted})
        worker = channels.run_in_thread()
        nanny.start_nanny()
        worker.stop()
        reload(nanny)
