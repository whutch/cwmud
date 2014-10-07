# -*- coding: utf-8 -*-
"""Tests for network communication and socket management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from telnetlib import Telnet
from time import sleep

import pytest

from atria.core.net import SocketManager


def test_create_socket_manager():
    """Test that we can create a socket manager.

    This is currently redundant, importing the net package already creates one,
    but we can keep the it for symmetry and in case that isn't always so.

    """
    sockets = SocketManager()
    assert sockets


class TestSockets:

    """A collection of tests for sockets and network communication."""

    sockets = SocketManager()
    opened_sockets = []
    client = Telnet()
    address = "localhost"
    # Use a port here that is different than the one in settings, in case the
    # tests are run while a real server is running on the same system.
    port = 4444

    @classmethod
    def _on_connect(cls, socket):
        cls.opened_sockets.append(socket)

    @classmethod
    def _on_disconnect(cls, socket):
        cls.opened_sockets.remove(socket)

    def test_listen_bad_callback(self):
        """Test that opening the listener with a bad callback fails."""
        with pytest.raises(TypeError):
            self.sockets.listen(self.address, self.port, None, lambda: None)
        with pytest.raises(TypeError):
            self.sockets.listen(self.address, self.port, lambda: None, None)

    def test_listen(self):
        """Test that we can open the listener socket."""
        self.sockets.listen(self.address, self.port,
                            self._on_connect, self._on_disconnect)
        assert self.sockets.listening
        assert self.sockets.address == self.address
        assert self.sockets.port == self.port

    def test_open_socket(self):
        """Test that we can accept new socket connections."""
        assert not self.opened_sockets
        self.client.open(self.address, self.port)
        sleep(0.1)  # Try bumping this up if this test fails.
        self.sockets.poll()
        assert self.opened_sockets

    def test_read_from_socket(self):
        """Test that we can read from a socket."""
        self.client.write("ping".encode("ascii") + b"\n")
        sleep(0.1)  # Try bumping this up if this test fails.
        self.sockets.poll()
        socket = self.opened_sockets[0]
        assert socket.cmd_ready
        assert socket.get_command() == "ping"

    def test_write_to_socket(self):
        """Test that we can write to a socket."""
        socket = self.opened_sockets[0]
        socket.send("pong\n")
        sleep(0.1)  # Try bumping this up if this test fails.
        self.sockets.poll()
        assert self.client.read_eager().decode("ascii").rstrip() == "pong"

    def test_close_socket(self):
        """Test that we can detect a dropped socket."""
        self.client.close()
        self.sockets.poll()
        assert not self.opened_sockets

    def test_socket_manager_close(self):
        """Test that we can close the listener socket."""
        assert self.sockets.listening
        self.sockets.close()
        assert not self.sockets.listening
