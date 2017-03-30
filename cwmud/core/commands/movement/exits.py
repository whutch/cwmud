# -*- coding: utf-8 -*-
"""Exits command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class ExitsCommand(Command):

    """A command to display the exits of the room a character is in."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.show_exits(short=True if self.args and
                        self.args[0] == "short" else False)


CharacterShell.add_verbs(ExitsCommand, "exits", "ex")
