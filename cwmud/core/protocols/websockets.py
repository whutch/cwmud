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


logging.getLogger("asyncio").setLevel(logging.WARN)
logging.getLogger("websockets").setLevel(logging.WARN)

log = get_logger("websocket")


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

    def start(self):
        """Start the WebSocket server."""
        super().start()
        # There's not much to set up here, it's all handled in `serve`.
        log.info("WebSocket server listening at %s:%s.",
                 self._host, self._port)

    def stop(self):
        """Stop the WebSocket server."""
        super().stop()
        log.info("Shutting down WebSocket server.")

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
        self.start()
        loop = asyncio.get_event_loop()
        asyncio_ensure_future(websockets.serve(self._accept_socket,
                                               self._host, self._port,
                                               ssl=self._ssl_context))
        try:
            loop.run_until_complete(self._poll_forever())
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    @asyncio.coroutine
    def _accept_socket(self, websocket, path):
        handler = WebSocketHandler(websocket)
        self._handlers.add(handler)
        BROKER.publish("ws:connect", "{}:{}:{}".format(
            handler.uid, *websocket.remote_address))
        while handler.alive:
            # Keep the websocket alive.
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def _poll_forever(self):
        while True:
            yield from self.poll()
            yield from asyncio.sleep(0.025)


class WebSocketHandler(ProtocolHandler):

    """A client handler for the WebSocket protocol."""

    def __init__(self, websocket):
        """Create a new WebSocket client handler."""
        super().__init__(uid=hash(websocket))
        self._websocket = websocket
        self._messages.subscribe("ws:output:{}".format(self._uid))

    @property
    def alive(self):
        """Return whether this handler's socket is open or not."""
        return self._websocket.open

    @asyncio.coroutine
    def _process_input(self):
        try:
            data = yield from self._websocket.recv()
            BROKER.publish("ws:input:{}".format(self._uid), data)
        except asyncio.queues.QueueEmpty:
            pass

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
        done, pending = yield from asyncio.wait(
            [self._process_input(), self._process_output()],
            return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()