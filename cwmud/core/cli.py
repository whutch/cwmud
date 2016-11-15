# -*- coding: utf-8 -*-
"""Command-line option and argument handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import argparse

from .. import __version__, settings


class CommandLineInterface:

    """A command-line interface manager."""''

    def __init__(self, program, usage, description):
        self._parser = argparse.ArgumentParser(
            prog=program, usage=usage, description=description,
            fromfile_prefix_chars="@", add_help=False)
        self._args = None

    @property
    def args(self):
        """Return the parsed arguments passed to this CLI."""
        if self._args is None:
            raise ValueError("cannot get args before parsing")
        return self._args

    def parse(self, known_only=False):
        """Parse the command-line arguments using current configuration.

        :param bool known_only: Whether to only parse known args or not;
                                if False, unknown args will cause an exit
        :returns None:

        """
        if known_only or settings.TESTING:
            self._args = self._parser.parse_known_args()[0]
        else:
            self._args = self._parser.parse_args()

    def add_argument_group(self, description):
        """Add an argument group to this CLI's parser.

        :param str description: A group description printed in help output
        :returns argparse._ArgumentGroup: The newly added group

        """
        return self._parser.add_argument_group(description)


CLI = CommandLineInterface(
    "cwmud", "python -m cwmud [OPTIONS]",
    "Initialize the Clockwork MUD server.")


# General options.
GENERAL_GROUP = CLI.add_argument_group("General Options")
GENERAL_GROUP.add_argument(
    "-h", "--help", action="help",
    help="Show this help message and exit")
GENERAL_GROUP.add_argument(
    "--version", action="version",
    help="Show the version number and exit",
    version="Clockwork MUD server {}".format(__version__))


# Game and contrib module options.
MODULE_GROUP = CLI.add_argument_group("Module Options")
MODULE_GROUP.add_argument(
    "-l", "--list-modules", action="store_true",
    help="Show a list of available modules and exit")
MODULE_GROUP.add_argument(
    "-g", "--game", metavar="MODULE", action="append",
    help="Load a game module")
MODULE_GROUP.add_argument(
    "-c", "--contrib", metavar="MODULE", action="append",
    help="Load a contrib module")


# Verbosity and printing options.
VERBOSITY_GROUP = CLI.add_argument_group("Verbosity Options")
VERBOSITY_GROUP.add_argument(
    "-v", "--verbose", action="store_true",
    help="Print as much information as possible")
VERBOSITY_GROUP.add_argument(
    "-q", "--quiet", action="store_true",
    help="Print as little information as possible")


# Logging options.
LOGGING_GROUP = CLI.add_argument_group("Logging Options")
LOGGING_GROUP.add_argument(
    "--log-dir", default="./logs", metavar="PATH",
    help="Path to the logging directory")
LOGGING_GROUP.add_argument(
    "-L", "--log-level", default="info", metavar="LEVEL",
    choices=("info", "debug"),
    help="Logging level")


# Networking options.
NETWORKING_GROUP = CLI.add_argument_group("Networking Options")
NETWORKING_GROUP.add_argument(
    "-H", "--host", default=settings.DEFAULT_HOST, metavar="ADDRESS",
    help="Hostname to bind the servers to")
NETWORKING_GROUP.add_argument(
    "-p", "--port", default=settings.DEFAULT_PORT, metavar="N",
    help="Port to bind the Telnet server to")
NETWORKING_GROUP.add_argument(
    "--ws", action="store_true",
    help="Whether to include a WebSocket server")
NETWORKING_GROUP.add_argument(
    "--ws-port", default=4443, metavar="N",
    help="Port to bind the WebSocket server to")
NETWORKING_GROUP.add_argument(
    "--ssl-cert", metavar="PATH",
    help="SSL certificate to use for encryption")
NETWORKING_GROUP.add_argument(
    "--ssl-key", metavar="PATH",
    help="Key file for SSL certificate if needed")


# Storage options.
STORAGE_GROUP = CLI.add_argument_group("Storage Options")
STORAGE_GROUP.add_argument(
    "-D", "--data-dir", default="./data", metavar="PATH",
    help="Path to the data directory")


# Do a partial parse of command-line arguments.  A final parse will be
# performed after all contrib and game modules are loaded by the server.
CLI.parse(known_only=True)
