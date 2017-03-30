# -*- coding: utf-8 -*-
"""Goto command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell
from ...world import Room


@COMMANDS.register
class GotoCommand(Command):

    """A command to teleport to somewhere else."""

    def _action(self):
        try:
            coords = self.args[0].split(",")
            if len(coords) == 2:
                coords.append("0")
            elif len(coords) != 3:
                raise IndexError
            x, y, z = map(int, coords)
            room = Room.get(x=x, y=y, z=z)
            if not room:
                self.session.send("That doesn't seem to be a place.")
                return
            poof_out = "{s} disappear{ss} in a puff of smoke."
            poof_in = "{s} arrive{ss} in a puff of smoke."
            self.session.char.move_to_room(room, poof_out, poof_in)
        except IndexError:
            self.session.send("Syntax: goto (x),(y)[,z]")


CharacterShell.add_verbs(GotoCommand, "goto", truncate=False)
