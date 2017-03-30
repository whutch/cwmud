# -*- coding: utf-8 -*-
"""Primary movement command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class DownCommand(Command):

    """A command to allow a character to move down."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(z=-1)


@COMMANDS.register
class EastCommand(Command):

    """A command to allow a character to move east."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=1)


@COMMANDS.register
class NorthCommand(Command):

    """A command to allow a character to move north."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(y=1)


@COMMANDS.register
class SouthCommand(Command):

    """A command to allow a character to move south."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(y=-1)


@COMMANDS.register
class WestCommand(Command):

    """A command to allow a character to move west."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=-1)


@COMMANDS.register
class UpCommand(Command):

    """A command to allow a character to move up."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(z=1)


CharacterShell.add_verbs(DownCommand, "down", "d")
CharacterShell.add_verbs(EastCommand, "east", "e")
CharacterShell.add_verbs(NorthCommand, "north", "n")
CharacterShell.add_verbs(SouthCommand, "south", "s")
CharacterShell.add_verbs(WestCommand, "west", "w")
CharacterShell.add_verbs(UpCommand, "up", "u")
