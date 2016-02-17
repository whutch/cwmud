# -*- coding: utf-8 -*-
"""Communication channel management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from weakref import WeakSet

from ..libs.miniboa import strip_caret_codes
from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import joins


log = get_logger("channels")


class ChannelManager:

    """A manager for channels.

    This is a convenience manager and is not required for the server to
    function.  All of its functionality can be achieved by subclassing,
    instantiating, and referencing channels directly.

    """

    def __init__(self):
        """Create a new channel manager."""
        self._channels = {}

    def __contains__(self, channel):
        return channel in self._channels

    def __getitem__(self, channel):
        return self._channels[channel]

    def register(self, name, channel):
        """Register a channel.

        :param str name: The name to register the channel under
        :param Channel channel: The channel to register
        :returns Channel: The registered channel
        :raises AlreadyExists: If a channel with `name` already exists
        :raises TypeError: If `channel` is not an instance of Channel

        """
        if not isinstance(channel, Channel):
            raise TypeError("must be an instance Channel to register")
        if name in self._channels:
            raise AlreadyExists(name, self._channels[name], channel)
        self._channels[name] = channel
        return channel


# We create a global ChannelManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more ChannelManager instances if you like.
CHANNELS = ChannelManager()


class Channel:

    """A communication channel."""

    def __init__(self, template="{msg}", members=None, logged=False):
        """Create a new channel.

        :param str template: A formatting string to use as a message template
        :param members: Optional, a list of sessions to fill members with;
                        if callable, it should return a list of sessions on-
                        demand in place of member tracking
        :param bool logged: Whether to log messages to the console or not
        :returns None:

        """
        self.template = template
        self.logged = logged
        if callable(members):
            self.members = members
        else:
            self.members = WeakSet()
            if members:
                for session in members:
                    self.members.add(session)

    def send(self, data, *more, sep=" ", context=None, members=None):
        """Send a message to a channel.

        `data` and all members of `more` will be converted to strings
        and joined together by `sep` via the joins function.

        :param any data: An initial chunk of data
        :param any more: Optional, any additional data to send
        :param str sep: Optional, a separator to join the resulting output by
        :param dict context: Optional, additional context to be passed to
                             the template formatter
        :param members: Optional, a list of sessions to use in place of the
                        channels own list; if callable, it should return a list
                        of sessions to use
        :returns None:

        """
        if not members:
            members = self.members
        if callable(members):
            members = members()
        message = joins(data, *more, sep=sep)
        context = context or {}
        message = self.template.format(msg=message, **context)
        if self.logged:
            log.info(strip_caret_codes(message))
        for session in members:
            session.send(message)
