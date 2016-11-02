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

from ..cli import CLI
from ..logs import get_logger
from ..messages import BROKER, get_pubsub
from . import ProtocolHandler, ProtocolServer


logging.getLogger("asyncio").setLevel(logging.WARN)
logging.getLogger("websockets").setLevel(logging.WARN)

log = get_logger("websocket")


class WebSocketServer(ProtocolServer):

    """A server for the WebSocket protocol."""

    def __init__(self, host=CLI.args.host, port=CLI.args.ws_port,
                 ssl_cert=CLI.args.ssl_cert, ssl_key=CLI.args.ssl_key):
        """Create a new WebSocket server."""
        super().__init__()
        self._host = host
        self._messages = get_pubsub()
        self._messages.subscribe("ws:close")
        self._port = port
        if ssl_cert is None:
            context = None
        else:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
            context.set_ciphers("RSA")
        self._ssl_context = context

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
        message = self._messages.get_message()
        while message:
            if message["channel"] == "ws:close":
                handler = self.get_handler(message["data"])
                if handler:
                    # Perform a final poll to flush any output
                    yield from handler.poll()
                    yield from handler.close()
                    self._handlers.remove(handler)
            message = self._messages.get_message()
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

    def close(self):
        """Forcibly close this handler's socket."""
        self._websocket.close()

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
