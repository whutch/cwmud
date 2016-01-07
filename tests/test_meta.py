# -*- coding: utf-8 -*-
"""Tests for the whole MUD process via a client."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from importlib import reload
from telnetlib import Telnet

import pytest
import redis

from atria import settings
import atria.__main__ as main


class TestMain:

    """A collection of tests for the server's nanny process."""

    client = Telnet()
    rdb = redis.StrictRedis(decode_responses=True)

    @pytest.mark.timeout(5)
    def test_meta(self):

        """Test several client interactions."""

        channels = self.rdb.pubsub(ignore_subscribe_messages=True)

        def _server_booted(msg):
            # We have to unsubscribe from the server-boot-complete event
            # so reloading doesn't loop forever.
            channels.unsubscribe("server-boot-complete")
            # Connect to the server.
            self.client.open(settings.BIND_ADDRESS, settings.BIND_PORT)
            # Create a new account.
            self.client.write(b"c\ntest@account.com\ntest@account.com\n")
            self.client.write(b"testaccount\nyes\n")
            self.client.write(b"testpassword\ntestpassword\nno\nyes\n")
            # Create a new character and log into it.
            self.client.write(b"c\ntestchar\nyes\n1\n")
            # Do some stuff.
            self.client.write(b"look\n")
            # Shutdown.
            self.client.write(b"shutdown now\n")

        channels.subscribe(**{"server-boot-complete": _server_booted})
        worker = channels.run_in_thread()
        main.main()
        worker.stop()
        reload(main)
