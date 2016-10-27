# -*- coding: utf-8 -*-
"""WebSocket protocol handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import asyncio
import ssl

import websockets

from ..messages import BROKER, get_pubsub


CERT_FILE = None
CERT_KEY = None


class WebSocketServer:

    """A server for the WebSocket protocol."""

    def __init__(self):
        self._handlers = set()

    @asyncio.coroutine
    def handle_websocket(self, websocket, path):
        """Handle the lifecycle of a WebSocket."""
        handler = WebSocketHandler(websocket)
        self._handlers.add(handler)
        BROKER.publish("ws:connect", "{}:{}:{}".format(
            handler.uid, *websocket.remote_address))
        try:
            loop = asyncio.get_event_loop()
            while True:
                if not handler.alive:
                    break
                tasks = [loop.create_task(handler.process_input()),
                         loop.create_task(handler.process_output())]
                done, _ = yield from asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in tasks:
                    if task not in done:
                        task.cancel()
                yield from asyncio.sleep(0.01)
        finally:
            BROKER.publish("ws:disconnect", handler.uid)
            self._handlers.remove(handler)

    def serve(self, host, port):
        """Start serving WebSockets."""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=CERT_KEY)
        context.set_ciphers("RSA")

        start_server = websockets.serve(self.handle_websocket,
                                        host, port, ssl=context)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        loop.run_forever()


class WebSocketHandler:

    """A client handler for the WebSocket protocol."""

    def __init__(self, websocket):
        self._uid = hash(websocket)
        self._messages = get_pubsub()
        self._websocket = websocket
        self._messages.subscribe("ws:output:{}".format(self._uid))

    @property
    def uid(self):
        """Return a unique identifier for this handler's socket."""
        return self._uid

    @property
    def alive(self):
        """Return where this handler's socket is open."""
        return self._websocket.open

    @asyncio.coroutine
    def process_input(self):
        data = yield from self._websocket.recv()
        BROKER.publish("ws:input:{}".format(self._uid), data)

    @asyncio.coroutine
    def process_output(self):
        message = self._messages.get_message()
        if message:
            yield from self._websocket.send(message["data"])
