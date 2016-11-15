# -*- coding: utf-8 -*-
"""Commands for administration."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from ..channels import CHANNELS
from ..characters import CharacterShell
from ..commands import Command, COMMANDS
from ..entities import ENTITIES
from ..server import SERVER
from ..storage import STORES
from ..timing import duration_to_pulses, PULSE_PER_SECOND, TIMERS
from ..world import Room


@COMMANDS.register
class AnnounceCommand(Command):

    """A command to announce something."""

    no_parse = True

    def _action(self):
        message = self.args[0].strip()
        CHANNELS["announce"].send(message)


@COMMANDS.register
class CommitCommand(Command):

    """A command to force a global store commit."""

    def _action(self):
        ENTITIES.save()
        STORES.commit()
        self.session.send("Ok.")


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


@COMMANDS.register
class ReloadCommand(Command):

    """A command to reload the game server, hopefully without interruption.

    This is similar to the old ROM-style copyover, except that we try and
    preserve a complete game state rather than just the open connections.

    """

    def _action(self):
        CHANNELS["announce"].send("Server is reloading, please remain calm!")
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


CharacterShell.add_verbs(AnnounceCommand, "announce")
CharacterShell.add_verbs(CommitCommand, "commit", truncate=False)
CharacterShell.add_verbs(GotoCommand, "go", "goto", truncate=False)
CharacterShell.add_verbs(ReloadCommand, "reload", truncate=False)
CharacterShell.add_verbs(ShutdownCommand, "shutdown", truncate=False)
