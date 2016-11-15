# -*- coding: utf-8 -*-
"""Universal client management and communication."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import deque
from time import time as now

from .events import EVENTS
from .logs import get_logger
from .messages import BROKER, get_pubsub
from .text import strip_caret_codes


log = get_logger("clients")


class Client:

    """A client handler."""

    PENDING, OPEN, CLOSING, CLOSED = range(4)

    def __init__(self, protocol, uid, host, port):
        """Create a new client handler."""
        self._commands = deque()
        self._host = host
        self._last_command_time = now()
        self._messages = get_pubsub()
        self._port = port
        self._protocol = protocol
        self._uid = uid
        self._messages.subscribe("{}:input:{}".format(protocol, uid))
        self.allow_formatting = False
        self.state = self.OPEN

    def __repr__(self):
        return "{}{}{}".format(self._host,
                               ":" if self._port is not None else "",
                               self._port if self._port is not None else "")

    @property
    def active(self):
        """Return whether this client is active or not."""
        return self.state == self.OPEN

    @property
    def uid(self):
        """Return the UID for this client."""
        return self._uid

    @property
    def host(self):
        """Return the host address of this client."""
        return self._host

    @property
    def port(self):
        """Return the port this client is connected to."""
        return self._port

    @property
    def command_pending(self):
        """Return whether there is a pending command or not."""
        return len(self._commands) > 0

    def close(self):
        """Forcibly close this client's connection."""
        BROKER.publish("{}:close".format(self._protocol), self._uid)
        self.state = self.CLOSING

    def get_command(self):
        """Get the next command in the queue, if there is one."""
        if len(self._commands) > 0:
            return self._commands.popleft()
        else:
            return None

    def get_idle_time(self):
        """Calculate how long this client has been idle, in seconds."""
        return now() - self._last_command_time

    def poll(self):
        """Process any queued IO for this client."""
        if self.state == self.OPEN:
            message = self._messages.get_message()
            while message:
                data = message["data"]
                self._commands.append(data)
                message = self._messages.get_message()
            if message:
                self._last_command_time = now()

    def send(self, data, strip_formatting=False):
        """Send data to this client.

        :param str data: The data to send
        :param bool strip_formatting: Whether to strip formatting codes out
                                      of the data before sending
        :returns None:

        """
        if strip_formatting or not self.allow_formatting:
            data = strip_caret_codes(data)
        BROKER.publish("{}:output:{}".format(self._protocol, self._uid), data)


class ClientManager:

    """A manager for client handlers."""

    def __init__(self, protocol, client_class=Client):
        """Create a new client manager."""
        self._client_class = client_class
        self._clients = {}
        self._messages = get_pubsub()
        self._protocol = protocol
        self._messages.subscribe("{}:connect".format(protocol))
        self._messages.subscribe("{}:disconnect".format(protocol))

    def _add_client(self, uid, host, port):
        if uid in self._clients:
            log.warning("UID collision! {}:{}".format(self._protocol, uid))
        client = self._client_class(self._protocol, uid, host, port)
        self._clients[uid] = client
        with EVENTS.fire("client_connected", client, no_pre=True):
            log.info("Incoming connection from %s.", client)

    def _remove_client(self, uid):
        client = self._clients.get(uid)
        if not client:
            return
        with EVENTS.fire("client_disconnected", client, no_pre=True):
            log.info("Lost connection from %s.", client)
            client.state = client.CLOSED
        del self._clients[uid]

    def find_by_uid(self, uid):
        """Find a client handler by its UID.

        :param str uid: The UID of the client to find
        :returns Client: The found client or None

        """
        return self._clients.get(uid)

    def check_connections(self):
        """Check for new/disconnected clients."""
        message = self._messages.get_message()
        while message:
            channel = message["channel"]
            data = message["data"]
            if channel == "{}:connect".format(self._protocol):
                uid, host, port = data.split(":")
                self._add_client(uid, host, port)
            elif channel == "{}:disconnect".format(self._protocol):
                self._remove_client(data)
            message = self._messages.get_message()

    def poll(self):
        """Process any queued IO for all clients."""
        check = list(self._clients.values())
        for client in check:
            if client.state == client.OPEN:
                client.poll()
            elif client.state == client.CLOSING:
                client.state = client.CLOSED
                del self._clients[client.uid]
