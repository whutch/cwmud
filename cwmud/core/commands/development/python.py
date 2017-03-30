# -*- coding: utf-8 -*-
"""Python command."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .. import Command, COMMANDS
from ...characters import CharacterShell


@COMMANDS.register
class PyCommand(Command):

    """A command for executing Python code."""

    no_parse = True

    def _action(self):
        # this is super dangerous don't commit this!!
        if not self.args[0]:
            self.session.send("No code to execute.")
            return
        import os  # noqa
        import re  # noqa
        import sys  # noqa
        from ...accounts import Account  # noqa
        from ...entities import ENTITIES, Entity, Unset  # noqa
        from ...storage import STORES  # noqa
        from ...shells import SHELLS  # noqa
        from ...commands import COMMANDS  # noqa
        from ...server import SERVER  # noqa
        from ...world import Room  # noqa
        char = self.session.char  # noqa
        s = self.session.send  # noqa
        try:
            code = compile(self.args[0][1:].strip('"') + "\n",
                           "<string>", "exec")
            result = exec(code) or "Ok."
            self.session.send(result)
        except Exception as exc:
            self.session.send(type(exc).__name__, ": ", exc.args[0], sep="")


CharacterShell.add_verbs(PyCommand, "py", "python", truncate=False)
