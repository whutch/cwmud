# -*- coding: utf-8 -*-
"""Tests for network communication and client management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from telnetlib import Telnet
from time import sleep

import pytest

from atria.core.net import ClientManager


class TestClients:

    """A collection of tests for networking and client communication."""

    clients = None
    opened_clients = []
    client = Telnet()
    address = "localhost"
    # Use a port here that is different than the one in settings, in case the
    # tests are run while a real server is running on the same system.
    port = 4444

    @classmethod
    def _on_connect(cls, client):
        cls.opened_clients.append(client)

    @classmethod
    def _on_disconnect(cls, client):
        cls.opened_clients.remove(client)

    def test_create_client_manager(self):
        """Test that we can create a new client manager.

        This is currently redundant, importing the net package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).clients = ClientManager()
        assert self.clients

    def test_listen_bad_callback(self):
        """Test that opening the listener with a bad callback fails."""
        with pytest.raises(TypeError):
            self.clients.listen(self.address, self.port, None, lambda: None)
        with pytest.raises(TypeError):
            self.clients.listen(self.address, self.port, lambda: None, None)

    def test_listen(self):
        """Test that we can open the listener socket."""
        self.clients.listen(self.address, self.port,
                            self._on_connect, self._on_disconnect)
        assert self.clients.listening
        assert self.clients.address == self.address
        assert self.clients.port == self.port

    def test_client_connect(self):
        """Test that we can accept new client connections."""
        assert not self.opened_clients
        self.client.open(self.address, self.port)
        sleep(0.1)  # Try bumping this up if this test fails.
        self.clients.poll()
        assert self.opened_clients

    def test_read_from_client(self):
        """Test that we can read from a client."""
        self.client.write("ping".encode("ascii") + b"\n")
        sleep(0.1)  # Try bumping this up if this test fails.
        self.clients.poll()
        client = self.opened_clients[0]
        assert client.cmd_ready
        assert client.get_command() == "ping"

    def test_write_to_client(self):
        """Test that we can write to a client."""
        client = self.opened_clients[0]
        client.send("pong\n")
        sleep(0.1)  # Try bumping this up if this test fails.
        self.clients.poll()
        assert self.client.read_eager().decode("ascii").rstrip() == "pong"

    def test_client_disconnect(self):
        """Test that we can detect a client disconnect."""
        self.client.close()
        self.clients.poll()
        assert not self.opened_clients

    def test_client_manager_close(self):
        """Test that we can close the listener socket."""
        assert self.clients.listening
        self.clients.close()
        assert not self.clients.listening
