# -*- coding: utf-8 -*-
"""Player characters."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import re

from .attributes import Attribute
from .channels import CHANNELS
from .characters import Character
from .entities import ENTITIES
from .events import EVENTS
from .logs import get_logger
from .requests import Request, REQUESTS
from .utils.funcs import joins


log = get_logger("players")


@ENTITIES.register
class Player(Character):

    """A player character."""

    _uid_code = "P"

    type = "player"

    def __repr__(self):
        if hasattr(self, "name") and self.name:
            return joins("Player<", self.name, ">", sep="")
        else:
            return "Player<(unnamed)>"

    def get_name(self):
        """Get this character's name."""
        return self.name

    def get_short_description(self):
        """Get this character's short description."""
        return "^G{} ^g{}^g is here.^~".format(self.name, self.title)

    def get_long_description(self):
        """Get this character's long description."""
        raise NotImplementedError

    def resume(self, quiet=False):
        """Bring this character into play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        with EVENTS.fire("char_login", self):
            if self.room:
                self.room.chars.add(self)
            self.active = True
            if not quiet:
                log.info("%s has entered the game.", self)
                CHANNELS["announce"].send(self.name, "has logged in.")
                self.show_room()

    def suspend(self, quiet=False):
        """Remove this character from play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        with EVENTS.fire("char_logout", self):
            if not quiet:
                log.info("%s has left the game.", self)
                CHANNELS["announce"].send(self.name, "has logged out.")
            self.active = False
            if self.room and self in self.room.chars:
                self.room.chars.remove(self)


@Player.register_attr("account")
class PlayerAccount(Attribute):

    """The account tied to a player."""

    @classmethod
    def validate(cls, entity, new_value):
        from .accounts import Account
        if not isinstance(new_value, Account):
            raise ValueError("Player account must be an Account instance.")
        return new_value

    @classmethod
    def serialize(cls, entity, value):
        # Save player accounts by UID.
        return value.uid

    @classmethod
    def deserialize(cls, entity, value):
        from .accounts import Account
        return Account.get(value)


@Player.register_attr("name")
class PlayerName(Attribute):

    """A player name."""

    _min_len = 2
    _max_len = 16
    _valid_chars = re.compile(r"^[a-zA-Z]+$")

    # Other modules can add any reservations they need to this list.
    # Reserved names should be in Titlecase.
    RESERVED = []

    @classmethod
    def validate(cls, entity, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("Character names can only contain letters.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("Character names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "letters in length."))
        new_value = new_value.title()
        if PlayerName.check_reserved(new_value):
            raise ValueError("That name is reserved.")
        if Player.find(name=new_value):
            raise ValueError("That name is already in use.")
        return new_value

    @classmethod
    def check_reserved(cls, name):
        """Check if a player name is reserved.

        :param str name: The player name to check
        :returns bool: True if the name is reserved, else False

        """
        return name in cls.RESERVED


# noinspection PyProtectedMember
@REQUESTS.register
class RequestNewPlayerName(Request):

    """A request for a new player name."""

    initial_prompt = joins("Enter a new character name (character names must"
                           " be between", PlayerName._min_len, "and",
                           PlayerName._max_len, "letters in length): ")
    repeat_prompt = "New character name: "
    confirm = Request.CONFIRM_YES
    confirm_prompt_yn = "'{data}', is that correct? (Y/N) "

    def _validate(self, data):
        try:
            new_name = PlayerName.validate(None, data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
        return new_name


@Player.register_attr("title")
class PlayerTitle(Attribute):

    """A player title."""

    _default = "the newbie"


# noinspection PyUnresolvedReferences
def create_player(session, callback, player=None):
    """Perform a series of requests to create a new player.

    :param sessions.Session session: The session creating a player
    :param callable callback: A callback for when the player is created
    :param Player player: The player in the process of being created
    :returns None:

    """
    if not player:
        player = Player()
        player._savable = False
    if not player.name:
        def _set_name(_session, new_name):
            player.name = new_name
            create_player(_session, callback, player)
        session.request(RequestNewPlayerName, _set_name)
    else:
        player.account = session.account
        player._savable = True
        callback(session, player)
