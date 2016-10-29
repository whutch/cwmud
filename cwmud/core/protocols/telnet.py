# -*- coding: utf-8 -*-
"""Telnet protocol handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from ...libs.miniboa import TelnetServer as _TelnetServer
from ..logs import get_logger
from ..messages import BROKER
from ..protocols import ProtocolHandler, ProtocolServer


log = get_logger("telnet")


class TelnetServer(ProtocolServer):

    """A manager for networking and client communication."""

    def __init__(self, host="localhost", port=4000):
        """Create a new Telnet server."""
        super().__init__()
        self._handlers = set()
        self._host = host
        self._port = port
        self._server = None

    def start(self):
        """Start the Telnet server."""
        self._server = _TelnetServer(address=self._host,
                                     port=self._port,
                                     timeout=0,
                                     on_connect=self._accept_client,
                                     on_disconnect=self._lost_client)
        log.info("Telnet server listening at %s:%s.", self._host, self._port)
        super().start()

    def stop(self):
        """Stop the Telnet server."""
        super().stop()
        self._server.stop()
        self._server = None

    def poll(self):
        """Poll the Telnet server to process any queued IO."""
        if self._server:
            self._server.poll()
        check = self._handlers.copy()
        for handler in check:
            if not handler.alive:
                BROKER.publish("telnet:disconnect", handler.uid)
                self._handlers.remove(handler)
            else:
                handler.poll()

    def _find_by_client(self, client):
        for handler in self._handlers:
            if handler.client is client:
                return handler

    def _accept_client(self, client):
        handler = TelnetHandler(client)
        self._handlers.add(handler)
        BROKER.publish("telnet:connect", "{}:{}:{}".format(
            handler.uid, client.address, client.port))

    def _lost_client(self, client):
        handler = self._find_by_client(client)
        if handler:
            BROKER.publish("telnet:disconnect", handler.uid)
            self._handlers.remove(handler)


class TelnetHandler(ProtocolHandler):

    """A client handler for the Telnet protocol."""

    def __init__(self, client):
        """Create a new Telnet client handler."""
        super().__init__(uid=hash(client))
        self._client = client
        self._messages.subscribe("telnet:output:{}".format(self._uid))

    @property
    def alive(self):
        """Return whether this handler's client is alive or not."""
        return self._client.active

    @property
    def client(self):
        """Return the miniboa.TelnetClient used by this handler."""
        return self._client

    def poll(self):
        """Poll this handler to process any queued IO."""
        while self._client.cmd_ready:
            command = self._client.get_command()
            BROKER.publish("telnet:input:{}".format(self._uid), command)
        message = self._messages.get_message()
        while message:
            self._client.send_cc(message["data"])
            message = self._messages.get_message()
