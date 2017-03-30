# -*- coding: utf-8 -*-
"""Who command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell
from ...sessions import SESSIONS


@COMMANDS.register
class WhoCommand(Command):

    """A command to display the active players."""

    def _action(self):
        chars = [session.char for session in SESSIONS.all()
                 if session.char and session.char.active]
        self.session.send("Players online:", len(chars))
        for char in chars:
            self.session.send("  ^W", char.name, "^~  ", char.title, sep="")


CharacterShell.add_verbs(WhoCommand, "who")
