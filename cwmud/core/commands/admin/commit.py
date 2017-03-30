# -*- coding: utf-8 -*-
"""Commit command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell
from ...entities import ENTITIES
from ...storage import STORES


@COMMANDS.register
class CommitCommand(Command):

    """A command to force a global store commit."""

    def _action(self):
        ENTITIES.save()
        STORES.commit()
        self.session.send("Ok.")


CharacterShell.add_verbs(CommitCommand, "commit", truncate=False)
