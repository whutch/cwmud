# -*- coding: utf-8 -*-
"""Transport protocol implementations."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from time import sleep

from ..logs import get_logger
from ..messages import get_pubsub


log = get_logger("protocols")


class ProtocolServer:

    """A server for a specific transport protocol.

    This is an abstract base class.

    """

    def __init__(self):
        """Create a new server."""
        self._handlers = set()
        self._started = False

    @property
    def is_started(self):
        """Return whether the server is started or not."""
        return self._started

    def get_handler(self, uid):
        """Find a handler by its UID.

        :param uid: The UID to search for
        :returns WebSocketHandler: The found handler or None

        """
        for handler in self._handlers:
            if handler.uid == uid:
                return handler

    def start(self):
        """Start the server."""
        self._started = True

    def stop(self):
        """Stop the server."""
        self._started = False

    def poll(self):
        """Poll the server to process any queued IO."""
        raise NotImplementedError

    def serve(self):
        """Continuously serve protocol IO.

        This should be a blocking function that runs until the
        server is stopped.

        """
        if not self.is_started:
            self.start()
        try:
            while self.is_started:
                self.poll()
                sleep(0.025)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


class ProtocolHandler:

    """A client handler for a specific transport protocol.

    This is an abstract base class.

    """

    def __init__(self, uid=None):
        """Create a new client handler."""
        self._messages = get_pubsub()
        self._uid = uid

    @property
    def uid(self):
        """Return a unique identifier for this client."""
        return self._uid

    @property
    def alive(self):
        """Return whether this handler's client is alive or not."""
        return False

    def poll(self):
        """Poll this handler to process any queued IO."""
        raise NotImplementedError
