# -*- coding: utf-8 -*-
"""Commands for communication."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from ..channels import Channel, CHANNELS
from ..characters import Character, CharacterShell
from ..commands import Command, COMMANDS


GOSSIP = Channel("^M[Gossip]^W {speaker}^w: {msg}^~", logged=True)
CHANNELS.register("gossip", GOSSIP)


@COMMANDS.register
class GossipCommand(Command):

    """A command for global communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        sessions = [_char.session for _char in Character.all()]
        CHANNELS["gossip"].send(message, context={"speaker": char.name},
                                members=sessions)


@COMMANDS.register
class SayCommand(Command):

    """A command for room-specific communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        char.act("{s} say{ss}, '{msg}'.", {"msg": message},
                 to=char.room.chars)


CharacterShell.add_verbs(GossipCommand, "gossip", "\"")
CharacterShell.add_verbs(SayCommand, "say", "'")
