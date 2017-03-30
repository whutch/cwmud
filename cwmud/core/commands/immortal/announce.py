# -*- coding: utf-8 -*-
"""Announce command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...channels import CHANNELS
from ...characters import CharacterShell


@COMMANDS.register
class AnnounceCommand(Command):

    """A command to announce something."""

    no_parse = True

    def _action(self):
        message = self.args[0].strip()
        CHANNELS["announce"].send(message)


CharacterShell.add_verbs(AnnounceCommand, "announce")
