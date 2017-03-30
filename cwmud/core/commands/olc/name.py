# -*- coding: utf-8 -*-
"""Name command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class NameCommand(Command):

    """A command for naming things."""

    no_parse = True

    def _action(self):
        # This will later be a general OLC command for naming anything but
        # for now you can just name rooms.
        char = self.session.char
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.room.name = self.args[0].strip().title()
        self.session.send("Ok.")


CharacterShell.add_verbs(NameCommand, "name")
