# -*- coding: utf-8 -*-
"""Test command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class TestCommand(Command):

    """A command to test something."""

    def _action(self):
        self.session.send("Great success!")


CharacterShell.add_verbs(TestCommand, "test", truncate=False)
