# -*- coding: utf-8 -*-
"""Quit command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell
from ...utils import joins


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the game."""

    def _action(self):
        self.session.close("Okay, goodbye!",
                           log_msg=joins(self.session, "has quit."))


CharacterShell.add_verbs(QuitCommand, "quit", truncate=False)
