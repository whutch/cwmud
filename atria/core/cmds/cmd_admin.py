# -*- coding: utf-8 -*-
"""Commands for administration."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from ..characters import CharacterShell
from ..commands import Command, COMMANDS
from ..entities import ENTITIES
from ..server import SERVER
from ..storage import STORES
from ..timing import duration_to_pulses, PULSE_PER_SECOND, TIMERS


@COMMANDS.register
class CommitCommand(Command):

    """A command to force a global store commit."""

    def _action(self):
        ENTITIES.save()
        STORES.commit()
        self.session.send("Ok.")


@COMMANDS.register
class ReloadCommand(Command):

    """A command to reload the game server, hopefully without interruption.

    This is similar to the old ROM-style copyover, except that we try and
    preserve a complete game state rather than just the open connections.

    """

    def _action(self):
        self.session.send("Starting server reload, hold on to your butt.")
        SERVER.reload()


@COMMANDS.register
class ShutdownCommand(Command):

    """A command to shutdown the game server."""

    def _action(self):
        arg = self.args[0].lower() if self.args else None
        if arg and arg in ("stop", "cancel"):
            if "shutdown" not in TIMERS:
                self.session.send("There is no shutdown in progress.")
            else:
                TIMERS.kill("shutdown")
                self.session.send("Shutdown canceled.")
            return
        try:
            if arg is None:
                # Default to 10 seconds.
                when = duration_to_pulses("10s")
            else:
                when = duration_to_pulses(self.args[0])
        except ValueError:
            self.session.send("Invalid time until shutdown.")
        else:
            if when:
                self.session.send("Shutdown initiated in",
                                  when // PULSE_PER_SECOND, "seconds!")

            @TIMERS.create(when, "shutdown")
            def _shutdown():
                self.session.send("Server is shutting down!")
                SERVER.shutdown()


CharacterShell.add_verbs(CommitCommand, "commit", truncate=False)
CharacterShell.add_verbs(ReloadCommand, "reload", truncate=False)
CharacterShell.add_verbs(ShutdownCommand, "shutdown", truncate=False)