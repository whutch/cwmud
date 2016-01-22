# -*- coding: utf-8 -*-
"""Commands for basic MUD interaction."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from ..accounts import AccountMenu
from ..characters import CharacterShell
from ..commands import Command, COMMANDS
from ..events import EVENTS
from ..utils.funcs import joins


@COMMANDS.register
class LogoutCommand(Command):

    """A command for logging out of the game."""

    def _action(self):
        if self.session.char:
            self.session.char.suspend()
        EVENTS.fire("char_logout", self.char).now()
        self.session.shell = None
        self.session.menu = AccountMenu


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the game."""

    def _action(self):
        self.session.close("Okay, goodbye!",
                           log_msg=joins(self.session, "has quit."))


CharacterShell.add_verbs(LogoutCommand, "logout", truncate=False)
CharacterShell.add_verbs(QuitCommand, "quit", truncate=False)
