# -*- coding: utf-8 -*-
"""Server initialization and loop logic."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os.path import exists, join

from .. import __version__
from .. import settings
from .commands import COMMANDS, Command
from .events import EVENTS
from .logs import get_logger
from .net import SOCKETS
from .sessions import SESSIONS
from .shells import STATES, SHELLS, Shell, WeakValueDictionary
from .timing import TIMERS
from .utils.funcs import joins


log = get_logger("server")


@SHELLS.register
class BaseShell(Shell):

    """A basic command shell."""

    _verbs = WeakValueDictionary()
    state = STATES.playing


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the server."""

    def _action(self):
        self.session.close("Okay, goodbye!",
                           log_msg=joins(self.session, "has quit"))


@COMMANDS.register
class SayCommand(Command):

    """A command for saying stuff on the server."""

    no_parse = True

    def _action(self):
        message = self.args[0].strip()
        self.session.send(joins("You say, '", message, "'.", sep=""))


BaseShell.add_verbs(QuitCommand, "quit")
BaseShell.add_verbs(SayCommand, "say", "'")


def _open_socket(socket):
    """Fire an event when a new socket is opened."""
    with EVENTS.fire("socket_opened", socket, no_pre=True):
        log.info("Incoming connection from %s", socket.addrport())


def _close_socket(socket):
    """Fire and event when a socket is closed for any reason."""
    with EVENTS.fire("socket_closed", socket, no_pre=True):
        log.info("Lost connection from %s", socket.addrport())


@EVENTS.hook("socket_opened")
def _hook_socket_opened(socket):
    session = SESSIONS.create(socket, BaseShell)
    with EVENTS.fire("session_started", session):
        session.send(SESSIONS.greeting)


@EVENTS.hook("socket_closed")
def _hook_socket_closed(socket):
    session = SESSIONS.find_by_socket(socket)
    if session:
        session._socket = None


def boot():
    """Initialize and boot up the MUD server.

    Doesn't start looping until loop is called.

    """
    with EVENTS.fire("server_init", no_pre=True):
        log.info("%s %s", settings.MUD_NAME_FULL, __version__)
        log.info("Initializing server")

    with EVENTS.fire("server_boot"):
        log.info("Booting server")
        SOCKETS.listen(settings.BIND_ADDRESS,
                       settings.BIND_PORT,
                       _open_socket,
                       _close_socket)
        greeting_path = join(settings.DATA_DIR, "greeting.txt")
        if exists(greeting_path):
            with open(greeting_path) as greeting_file:
                SESSIONS.greeting = greeting_file.read()


def loop():
    """Start the main server loop and loop until stopped."""
    try:
        while True:
            with EVENTS.fire("server_loop"):
                TIMERS.pulse()  # Pulse each timer once and fire any callbacks
                SESSIONS.poll()  # Process IO for existing connections
                SOCKETS.poll()  # Check for any new/dropped connections
                SESSIONS.prune()  # Clean up closed/dead sessions
            # Any thing you want polled or updated should be done before
            # this point so that it is considered in the pulse delay.
            TIMERS.sleep_excess()  # Wait until the next pulse is ready
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, stopping")

    with EVENTS.fire("server_shutdown", no_post=True):
        log.info("Shutting down server")
