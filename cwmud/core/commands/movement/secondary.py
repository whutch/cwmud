# -*- coding: utf-8 -*-
"""Secondary movement commands."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class NortheastCommand(Command):

    """A command to allow a character to move northeast."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=1, y=1)


@COMMANDS.register
class NorthwestCommand(Command):

    """A command to allow a character to move northwest."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=-1, y=1)


@COMMANDS.register
class SoutheastCommand(Command):

    """A command to allow a character to move southeast."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=1, y=-1)


@COMMANDS.register
class SouthwestCommand(Command):

    """A command to allow a character to move southwest."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=-1, y=-1)


CharacterShell.add_verbs(NortheastCommand, "northeast", "ne")
CharacterShell.add_verbs(NorthwestCommand, "northwest", "nw")
CharacterShell.add_verbs(SoutheastCommand, "southeast", "se")
CharacterShell.add_verbs(SouthwestCommand, "southwest", "sw")
