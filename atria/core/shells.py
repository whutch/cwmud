# -*- coding: utf-8 -*-
"""Shell management and client input processing."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import joins
from .utils.mixins import HasFlags, HasParent


log = get_logger("shells")


class STATES:

    """A collection of values to describe the state a shell is in.

    This is a placeholder for a more sophisticated solution later.

    """

    connected = 0
    login = 1
    playing = 2


class ShellManager:

    """A manager for shell registration.

    Unlike the other object managers in the core modules, this manager is not
    required for the game to function. All of the functionality of shells can
    be achieved by subclassing, instantiating, and references shells directly,
    but having the manager allows for easy passing of shells between modules
    (the modules only need to import SHELLS instead of importing other modules
    directly to get to their shells).

    """

    def __init__(self):
        """Create a new shell manager."""
        self._shells = {}

    def __contains__(self, shell):
        return shell in self._shells

    def __getitem__(self, shell):
        return self._shells[shell]

    def register(self, shell=None):
        """Register a shell.

        If you do not provide ``shell``, this will instead return a
        decorator that will register the decorated class.

        :param Shell shell: Optional, the shell to be registered
        :returns Shell|function: The registered shell if a shell was provided,
                                  otherwise a decorator to register the shell
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Shell.

        """
        def _inner(shell_class):
            if (not isinstance(shell_class, type) or
                    not issubclass(shell_class, Shell)):
                raise TypeError("must be subclass of Shell to register")
            name = shell_class.__name__
            if name in self._shells:
                raise AlreadyExists(name, self._shells[name], shell_class)
            self._shells[name] = shell_class
            return shell_class
        if shell:
            return _inner(shell)
        else:
            return _inner


class Shell(HasFlags, HasParent):

    """A shell for processing client input."""

    commands = None
    pattern = re.compile(r"""
            # Because we're using a delimiter group, we need
            # to wrap the whole thing in a group, otherwise
            # re.findall will only return the subgroup
            (
                # First try and match text between a pair of
                # delimiters (", ', or `)
                (["'`]).*?\2
            |
                # Otherwise match anything not whitespace
                [^\s]+
            )
            # An re.findall of this will return tuple pairs
            # consisting of either a single word argument or
            # a delimited string (with delimiter) as the first
            # value and either an empty string (if single word)
            # or the delimiter (if delimited) as the second
        """, re.VERBOSE)
    state = STATES.connected

    def __init__(self):
        super().__init__()

    @property
    def session(self):
        """Return this shell's current session."""
        return self._get_weak("session")

    @session.setter
    def session(self, new_session):
        """Set the current shell for this session.

        :param _Session new_session: The session tied to this shell
        :returns: None

        """
        self._set_weak("session", new_session)

    # noinspection PyMethodMayBeStatic
    def init(self):
        """Initialize this shell for the session.

        This method is called when the shell is assigned; override it to do
        anything prior to the initial prompt.

        """
        return

    # noinspection PyMethodMayBeStatic
    def get_prompt(self):
        """Generate the current prompt for this shell."""
        return "^y>^~ "

    def get_arguments(self, data, max_args=-1):
        """Parse data into a list of arguments.

        Any un-parsed arguments (either because max was reached or because a
        delimiter was opened and not closed) will be returned as the last
        element of the resulting list.

        :param str data: The data to be broken down into arguments
        :param int max_args: The maximum number of arguments to parse,
                             if less than zero, all arguments are parsed
        :returns list: The parsed arguments

        """
        # Dump leading and trailing whitespace
        data = data.strip()
        # Is there anything left?
        if not data:
            return []
        if max_args == 0:
            return [data]
        args = []
        matches = self.pattern.finditer(data)
        last_match = None
        for match in matches:
            arg, delimiter = match.groups()
            if delimiter:
                arg = arg[1:-1]
            if arg:
                args.append(arg)
            last_match = match
            if max_args > 0:
                max_args -= 1
            if max_args == 0:
                break
        if last_match:
            rest = data[last_match.end():].strip()
            if rest:
                args.append(rest)
        return args

    def parse(self, data):
        """Parse input from the client session.

        :param str data: The data to be parsed
        :returns: None

        """
        # Placeholder until commands are added
        self.session.send("Huh?")


# We create a global ShellManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more ShellManager instances if you like.
SHELLS = ShellManager()


# This is an example shell that overrides parse and sets a higher state
@SHELLS.register
class EchoShell(Shell):

    """A simple shell that echos back anything the client sends."""

    state = STATES.playing

    def parse(self, data):
        """Echo any input back to the client.

        :param str data: Input from the client

        """
        if data.strip() == "quit":
            self.session.close("Okay, goodbye!",
                               log_msg=joins(self, "has quit"))
        else:
            self.session.send("You sent:", data)
