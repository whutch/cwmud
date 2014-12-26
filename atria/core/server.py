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
from .net import CLIENTS
from .sessions import SESSIONS
from .shells import STATES, SHELLS, Shell, WeakValueDictionary
from .timing import TIMERS
from .utils.exceptions import ServerShutdown, ServerReboot, ServerReload
from .utils.funcs import joins
from .opt.pickle import PickleStore


log = get_logger("server")
_store = PickleStore("server")


def boot():
    """Initialize and boot up the MUD server.

    Doesn't start looping until loop is called.

    """
    with EVENTS.fire("server_init", no_pre=True):
        log.info("%s %s", settings.MUD_NAME_FULL, __version__)
        log.info("Initializing server")

    def _client_connected(client):
        with EVENTS.fire("client_connected", client, no_pre=True):
            log.info("Incoming connection from %s", client.addrport())

    def _client_disconnected(client):
        with EVENTS.fire("client_disconnected", client, no_pre=True):
            log.info("Lost connection from %s", client.addrport())

    with EVENTS.fire("server_boot"):
        log.info("Booting server")
        CLIENTS.listen(settings.BIND_ADDRESS,
                       settings.BIND_PORT,
                       _client_connected,
                       _client_disconnected)
        greeting_path = join(settings.DATA_DIR, "greeting.txt")
        if exists(greeting_path):
            with open(greeting_path) as greeting_file:
                SESSIONS.greeting = greeting_file.read()
        if _store.has("state"):
            load_state()
            _store.delete("state")
            _store.commit()


def loop():
    """Start the main server loop and loop until stopped."""
    reloading = False
    try:
        while True:
            with EVENTS.fire("server_loop"):
                TIMERS.pulse()  # Pulse each timer once and fire any callbacks
                SESSIONS.poll()  # Process IO for existing connections
                CLIENTS.poll()  # Check for any new/dropped connections
                SESSIONS.prune()  # Clean up closed/dead sessions
            # Any thing you want polled or updated should be done before
            # this point so that it is considered in the pulse delay.
            TIMERS.sleep_excess()  # Wait until the next pulse is ready
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, stopping")
    except ServerShutdown:
        log.info("Received server shutdown")
    except ServerReboot:
        log.info("Received server reboot")
    except ServerReload:
        log.info("Reloading server")
        reloading = True
        # Do one last session and client poll to clear the output queues
        SESSIONS.poll(output_only=True)
        CLIENTS.poll()
        SESSIONS.prune()
        import subprocess
        new_process = subprocess.Popen(["python", "-m", "atria", "-R"])
        log.debug("New process spawned, PID is %s", new_process.pid)
        save_state(new_process.pid)
    finally:
        if not reloading:
            with EVENTS.fire("server_shutdown", no_post=True):
                log.info("Server shutdown complete")


def save_state(pass_to_pid=None):
    """Dump a serialized server state to file.

    This function just dumps a state dict into a pickle file, all the actual
    data processing and sanitizing should be done by individual modules
    post-hooking the server_save_state event; each module should add any data
    they want saved to the shared state dict before it is serialized.

    :param int pass_to_pid: Optional, the PID of a new MUD server process that
                            the state is being passed on to
    :returns: None

    """
    if _store.has("state"):
        raise KeyError("a server state file already exists")
    log.info("Starting game state save")
    state = {}
    with EVENTS.fire("server_save_state", state, pass_to_pid):
        _store.put("state", state)
        _store.commit()
    log.info("Game state save successful")


def load_state():
    """Load a serialized server state from file.

    This function just reads a pickle file into a state dict, all the actual
    data processing and sanitizing should be done by individual modules
    post-hooking the server_load_state event; each module should pull any data
    they want loaded from the shared state dict after it is deserialized.

    :returns: None

    """
    if not _store.has("state"):
        raise KeyError("no server state file exists")
    log.info("Starting game state load")
    state = _store.get("state")
    EVENTS.fire("server_load_state", state).now()
    log.info("Game state load successful")


@EVENTS.hook("client_connected")
def _hook_client_connected(client):
    session = SESSIONS.create(client)
    with EVENTS.fire("session_started", session):
        session.send(SESSIONS.greeting)
        from .accounts import AccountMenu
        session.menu = AccountMenu


@EVENTS.hook("client_disconnected")
def _hook_client_disconnected(client):
    session = SESSIONS.find_by_client(client)
    if session:
        session._socket = None


@SHELLS.register
class ChatShell(Shell):

    """A basic command shell for chatting."""

    _verbs = WeakValueDictionary()
    state = STATES.playing


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the server."""

    def _action(self):
        from .accounts import AccountMenu
        self.session.menu = AccountMenu
        self.session.shell = None


@COMMANDS.register
class ReloadCommand(Command):

    """A command to reload the game server, hopefully without interruption.

    This is similar to the old ROM-style copyover, except that we try and
    preserve a complete game state rather than just the open connections.

    """

    def _action(self):
        self.session.send("Starting server reload, hold on to your butt.")
        raise ServerReload


@COMMANDS.register
class SayCommand(Command):

    """A command for saying stuff on the server."""

    no_parse = True

    def _action(self):
        message = self.args[0].strip()
        self.session.send(joins("You say, '", message, "'.", sep=""))


@COMMANDS.register
class TestCommand(Command):

    """A command to test something."""

    def _action(self):
        self.session.send("Great success!")


@COMMANDS.register
class TimeCommand(Command):

    """A command to display the current server time.

    This can be replaced in a game shell to display special in-game time, etc.

    """

    def _action(self):
        from datetime import datetime as dt
        timestamp = dt.fromtimestamp(TIMERS.time).strftime("%c")
        self.session.send("Current time: ", timestamp,
                          " (", TIMERS.get_time_code(), ")", sep="")


ChatShell.add_verbs(QuitCommand, "quit")
ChatShell.add_verbs(ReloadCommand, "reload")
ChatShell.add_verbs(SayCommand, "say", "'")
ChatShell.add_verbs(TestCommand, "test")
ChatShell.add_verbs(TimeCommand, "time")


if settings.FORCE_GC_COLLECT:
    import gc
    TIMERS.create("1m", "gc_collect", repeat=-1, callback=gc.collect)
