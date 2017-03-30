# -*- coding: utf-8 -*-
"""Say command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class SayCommand(Command):

    """A command for room-specific communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        char.act("{s} say{ss}, '{msg}'.", {"msg": message},
                 to=char.room.chars)


CharacterShell.add_verbs(SayCommand, "say", "'")
