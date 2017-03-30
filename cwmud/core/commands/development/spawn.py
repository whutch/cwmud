# -*- coding: utf-8 -*-
"""Spawn command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class SpawnCommand(Command):

    """A command to test something."""

    def _action(self):
        from ...entities import ENTITIES
        entity = ENTITIES[self.args[0]]()
        entity.name = self.args[1]
        self.session.char.inventory.append(entity)
        self.session.send("Ok.")


CharacterShell.add_verbs(SpawnCommand, "spawn", truncate=False)
