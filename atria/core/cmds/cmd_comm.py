# -*- coding: utf-8 -*-
"""Commands for communication."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from ..characters import Character, CharacterShell
from ..commands import Command, COMMANDS


@COMMANDS.register
class GossipCommand(Command):

    """A command for global communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        char.act("^M{s} gossip{ss}, '{msg}'.^~", {"msg": message},
                 to=Character.all())


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
