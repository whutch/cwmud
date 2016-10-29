# -*- coding: utf-8 -*-
"""WebSocket protocol handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import asyncio
import logging
import ssl

import websockets
from websockets.compatibility import asyncio_ensure_future

from ..logs import get_logger
from ..messages import BROKER, get_pubsub
from . import ProtocolHandler, ProtocolServer


logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.INFO)

log = get_logger("websockets")


class WebSocketServer(ProtocolServer):

    """A server for the WebSocket protocol."""

    def __init__(self, host="localhost", port=4443,
                 ssl_cert=None, ssl_key=None):
        """Create a new WebSocket server."""
        super().__init__()
        self._handlers = set()
        self._host = host
        self._port = port
        if ssl_cert is None:
            context = None
        else:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
            context.set_ciphers("RSA")
        self._ssl_context = context
        self._messages = get_pubsub()
        self._messages.subscribe("ws:command")

    @asyncio.coroutine
    def poll(self):
        """Poll the server to process any queued IO."""
        check = self._handlers.copy()
        for handler in check:
            if not handler.alive:
                BROKER.publish("ws:disconnect", handler.uid)
                self._handlers.remove(handler)
            else:
                yield from handler.poll()

    def serve(self):
        """Continuously serve WebSocket IO."""
        loop = asyncio.get_event_loop()
        asyncio_ensure_future(websockets.serve(self._accept_socket,
                                               self._host, self._port,
                                               ssl=self._ssl_context))
        log.info("WebSocket server listening at %s:%s.", self._host, self._port)
        loop.run_until_complete(self._poll_forever())

    @asyncio.coroutine
    def _accept_socket(self, websocket, path):
        handler = WebSocketHandler(websocket)
        self._handlers.add(handler)
        BROKER.publish("ws:connect", "{}:{}:{}".format(
            handler.uid, *websocket.remote_address))
        while handler.alive:
            # Keep the websocket alive.
            yield from asyncio.sleep(0.01)

    @asyncio.coroutine
    def _poll_forever(self):
        while True:
            message = self._messages.get_message()
            while message:
                if message["channel"] == "ws:command":
                    command = message["data"]
                    if command == "debug":
                        from ...contrib.profiling import TRACKER
                        TRACKER.print_diff()
                message = self._messages.get_message()
            yield from self.poll()
            yield from asyncio.sleep(0.01)


class WebSocketHandler(ProtocolHandler):

    """A client handler for the WebSocket protocol."""

    def __init__(self, websocket):
        """Create a new WebSocket client handler."""
        super().__init__(uid=hash(websocket))
        self._websocket = websocket
        # Subscribe to messages to this socket.
        self._messages.subscribe("ws:output:{}".format(self._uid))

    @property
    def alive(self):
        """Return whether this handler's socket is open or not."""
        return self._websocket.open

    @asyncio.coroutine
    def _process_input(self):
        data = yield from self._websocket.recv()
        BROKER.publish("ws:input:{}".format(self._uid), data)

    @asyncio.coroutine
    def _process_output(self):
        message = self._messages.get_message()
        if message:
            yield from self._websocket.send(message["data"])

    @asyncio.coroutine
    def poll(self):
        """Poll this handler to process any queued IO."""
        if not self.alive:
            return
        tasks = [asyncio_ensure_future(self._process_input()),
                 asyncio_ensure_future(self._process_output())]
        done, pending = yield from asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
