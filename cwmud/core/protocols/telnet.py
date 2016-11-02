# -*- coding: utf-8 -*-
"""Telnet protocol handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from time import time as now

from ...libs.miniboa import TelnetServer as _TelnetServer
from ..cli import CLI
from ..logs import get_logger
from ..messages import BROKER, get_pubsub
from ..protocols import ProtocolHandler, ProtocolServer


log = get_logger("telnet")


class TelnetServer(ProtocolServer):

    """A manager for networking and client communication."""

    def __init__(self, host=CLI.args.host, port=CLI.args.port):
        """Create a new Telnet server."""
        super().__init__()
        self._host = host
        self._messages = get_pubsub()
        self._messages.subscribe("telnet:close")
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
        log.info("Shutting down Telnet server.")

    def poll(self):
        """Poll the Telnet server to process any queued IO."""
        if self._server:
            self._server.poll()
        message = self._messages.get_message()
        while message:
            if message["channel"] == "telnet:close":
                uid = int(message["data"])
                handler = self.get_handler(uid)
                if handler:
                    # Perform a final poll to flush any output
                    log.info("Closing connection from %s:%s.",
                             handler.host, handler.port)
                    handler.poll()
                    handler.close()
                    self._handlers.remove(handler)
            message = self._messages.get_message()
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
        # Miniboa seems to reuse clients somehow, so I can't just hash them
        # to get a UID.  Hashing the client and the current time will be
        # much more likely to be unique.
        uid = hash((client, now()))
        super().__init__(uid=uid)
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

    @property
    def host(self):
        """Return the host address of this handler's client."""
        return self._client.address

    @property
    def port(self):
        """Return the port this handler's client is connected to."""
        return self._client.port

    def close(self):
        """Forcibly close this handler's socket."""
        self._client.deactivate()

    def poll(self):
        """Poll this handler to process any queued IO."""
        while self._client.cmd_ready:
            command = self._client.get_command()
            BROKER.publish("telnet:input:{}".format(self._uid), command)
        message = self._messages.get_message()
        while message:
            self._client.send_cc(message["data"])
            message = self._messages.get_message()
