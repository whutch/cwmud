# -*- coding: utf-8 -*-
"""Communication channel management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from weakref import WeakSet

from .logs import get_logger
from .utils.funcs import joins


log = get_logger("channels")


class Channel:

    """A communication channel."""

    def __init__(self, header="", msg_color="^~", members=None):
        """Create a new channel.

        :param str header: A block of text to prepend to all messages
        :param str msg_color: A color code to use for messages
        :param members: Optional, a list of sessions to prefill members with;
                        if callable, it should return a list of sessions on-
                        demand in place of member tracking
        :returns None:

        """
        self.header = header
        self.msg_color = msg_color
        if callable(members):
            self.members = members
        else:
            self.members = WeakSet()
            if members:
                for session in members:
                    self.members.add(session)

    def send(self, data, *more, sep=" ", members=None):
        """Send a message to a channel.

        `data` and all members of `more` will be converted to strings
        and joined together by `sep` via the joins function.

        :param any data: An initial chunk of data
        :param any more: Optional, any additional data to send
        :param str sep: Optional, a separator to join the resulting output by

        :param members: Optional, a list of sessions to use in place of the
                        channels own list; if callable, it should return a list
                        of sessions to use
        :returns None:

        """
        if not members:
            members = self.members
        if callable(members):
            members = members()
        msg = joins(data, *more, sep=sep)
        for session in members:
            session.send(self.header, " ", self.msg_color, msg, "^~", sep="")
