# -*- coding: utf-8 -*-
"""Network communication and socket management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from ..libs.miniboa import TelnetServer
from .logs import get_logger


log = get_logger("net")


class SocketManager:

    """A manager for sockets and network communication."""

    def __init__(self):
        """Create a new socket manager."""
        self._listener = None
        self._address = ""
        self._port = 0

    @property
    def listening(self):
        """Return whether this is listening for new connections or not."""
        return self._listener is not None

    @property
    def address(self):
        """Return the address used to bind the listener socket."""
        return self._address

    @property
    def port(self):
        """Return the port used to listen for new connections."""
        return self._port

    def listen(self, address, port, on_connect, on_disconnect):
        """Start a new telnet server to listen for connections.

        This will discard any existing listener server, likely dropping any
        open connections.

        :param str address: The address to bind the listener socket to
        :param int port: The port to listen for new connections on
        :param callable on_connect: A callback for when a socket is opened
        :param callable on_disconnect: A callback for when a socket is closed
        :returns: None
        :raises TypeError: if on_connect or on_disconnect aren't callable

        """
        if not callable(on_connect):
            raise TypeError("on_connect callback must be callable")
        if not callable(on_disconnect):
            raise TypeError("on_disconnect callback must be callable")
        self._address = address
        self._port = port
        log.info("Binding listener to %s on port %s", address, port)
        self._listener = TelnetServer(address=address,
                                      port=port,
                                      timeout=0,
                                      on_connect=on_connect,
                                      on_disconnect=on_disconnect)

    def close(self):
        """Stop the telnet server."""
        log.info("Closing listener from %s on port %s", self.address, self.port)
        self._listener.stop()
        self._listener = None
        self._address = ""
        self._port = 0

    def poll(self):
        """Poll the telnet server to process any queued IO."""
        if self._listener:
            self._listener.poll()


# We create a global EventManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more EventManager instances if you like.
SOCKETS = SocketManager()
