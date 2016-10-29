# -*- coding: utf-8 -*-
"""Commands for information display."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from datetime import datetime as dt

from ..characters import CharacterShell
from ..commands import Command, COMMANDS
from ..sessions import SESSIONS
from ..timing import TIMERS


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


@COMMANDS.register
class LookCommand(Command):

    """A command to allow a character to look at things."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.show_room()


@COMMANDS.register
class TimeCommand(Command):

    """A command to display the current server time.

    This can be replaced in a game shell to display special in-game time, etc.

    """

    def _action(self):
        timestamp = dt.fromtimestamp(TIMERS.time).strftime("%c")
        self.session.send("Current time: ", timestamp,
                          " (", TIMERS.get_time_code(), ")", sep="")


@COMMANDS.register
class WhoCommand(Command):

    """A command to display the active players."""

    def _action(self):
        chars = [session.char for session in SESSIONS.all()
                 if session.char and session.char.active]
        self.session.send("Players online:", len(chars))
        for char in chars:
            self.session.send("  ^W", char.name, "^~  ", char.title, sep="")


CharacterShell.add_verbs(ExitsCommand, "exits", "ex")
CharacterShell.add_verbs(LookCommand, "look", "l")
CharacterShell.add_verbs(TimeCommand, "time")
CharacterShell.add_verbs(WhoCommand, "who")
