# -*- coding: utf-8 -*-
"""Get command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class GetCommand(Command):

    """A command to get an item."""

    def _action(self):
        # char = self.session.char
        self.session.send("Ok.")


CharacterShell.add_verbs(GetCommand, "get")
