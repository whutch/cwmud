# -*- coding: utf-8 -*-
"""Logout command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...accounts import AccountMenu
from ...characters import CharacterShell


@COMMANDS.register
class LogoutCommand(Command):

    """A command for logging out of the game."""

    def _action(self):
        if self.session.char:
            self.session.char.suspend()
        self.session.shell = None
        self.session.menu = AccountMenu


CharacterShell.add_verbs(LogoutCommand, "logout", truncate=False)
