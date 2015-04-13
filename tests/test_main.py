# -*- coding: utf-8 -*-
"""Tests for the server's main entry point."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from importlib import reload

import pytest
import redis

from atria import settings
import atria.__main__ as main


# Use a different listen port, in case the tests are run while a
# real server is running on the same system.
settings.BIND_PORT = 4445


class TestMain:

    """A collection of tests for the server's nanny process."""

    rdb = redis.StrictRedis(decode_responses=True)

    @pytest.mark.timeout(2)
    def test_main(self):

        """Test that the nanny process runs properly."""

        channels = self.rdb.pubsub(ignore_subscribe_messages=True)

        def _server_booted(msg):
            pid = int(msg["data"])
            self.rdb.publish("server-shutdown", pid)

        channels.subscribe(**{"server-boot-complete": _server_booted})
        worker = channels.run_in_thread()
        main.main()
        worker.stop()
        reload(main)

    @pytest.mark.timeout(2)
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
        main.main()
        worker.stop()
        reload(main)
