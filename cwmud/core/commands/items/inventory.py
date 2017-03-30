# -*- coding: utf-8 -*-
"""Inventory command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class InventoryCommand(Command):

    """A command to list a character's inventory."""

    def _action(self):
        char = self.session.char
        counts = char.inventory.get_counts()
        weight = char.inventory.get_weight()
        output = ["You are carrying:\n"]
        if counts:
            for name, count in sorted(counts):
                if count > 1:
                    output.append("^K(^~{:2}^K)^~ {}".format(count, name))
                else:
                    output.append("     {}".format(name))
        else:
            output.append("     nothing")
        output.append("\nWeight: {}/? stones".format(weight))
        self.session.send("\n".join(output))


CharacterShell.add_verbs(InventoryCommand, "inventory", "inv", "in", "i")
