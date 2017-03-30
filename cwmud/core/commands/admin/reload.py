# -*- coding: utf-8 -*-
"""Reload command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...channels import CHANNELS
from ...characters import CharacterShell
from ...server import SERVER


@COMMANDS.register
class ReloadCommand(Command):

    """A command to reload the game server, hopefully without interruption.

    This is similar to the old ROM-style copyover, except that we try and
    preserve a complete game state rather than just the open connections.

    """

    def _action(self):
        CHANNELS["announce"].send("Server is reloading, please remain calm!")
        SERVER.reload()


CharacterShell.add_verbs(ReloadCommand, "reload", truncate=False)
