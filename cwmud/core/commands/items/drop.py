# -*- coding: utf-8 -*-
"""Drop command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class DropCommand(Command):

    """A command to drop an item."""

    def _action(self):
        char = self.session.char
        if not char.room:
            self.session.send("You can't drop things here.")
            return
        for item in char.inventory:
            if self.args[0] in item.nouns:
                break
        else:
            self.session.send("You don't have that.")
            return
        self.session.send("You drop {}.".format(item.name))
        char.inventory.remove(item)
        item.delete()


CharacterShell.add_verbs(DropCommand, "drop")
