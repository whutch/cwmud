# -*- coding: utf-8 -*-
"""Shutdown command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...channels import CHANNELS
from ...characters import CharacterShell
from ...server import SERVER
from ...timing import duration_to_pulses, PULSE_PER_SECOND, TIMERS


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
                CHANNELS["announce"].send("Shutdown canceled.")
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

                CHANNELS["announce"].send(
                    "Shutdown initiated in",
                    when // PULSE_PER_SECOND, "seconds!")

            @TIMERS.create(when, "shutdown")
            def _shutdown():
                CHANNELS["announce"].send("Server is shutting down!")
                SERVER.shutdown()


CharacterShell.add_verbs(ShutdownCommand, "shutdown", truncate=False)
