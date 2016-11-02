# -*- coding: utf-8 -*-
"""Server initialization and loop logic."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from importlib import import_module
from gc import collect
from time import sleep

from .. import BASE_PACKAGE, settings
from . import const
from .accounts import AccountMenu, authenticate_account, create_account
from .attributes import Unset
from .channels import Channel, CHANNELS
from .cli import CLI
from .clients import Client, ClientManager
from .entities import ENTITIES
from .events import EVENTS
from .logs import get_logger
from .menus import Menu, MENUS
from .messages import BROKER, get_pubsub
from .pickle import PickleStore
from .sessions import SESSIONS
from .storage import STORES
from .timing import TIMERS
from .utils.exceptions import ServerReboot, ServerReload, ServerShutdown
from .utils.funcs import joins


log = get_logger("server")


class TelnetClient(Client):

    def __init__(self, protocol, uid, host, port):
        super().__init__(protocol, uid, host, port)
        self.allow_formatting = True


TEL_CLIENTS = ClientManager("telnet", client_class=TelnetClient)
WS_CLIENTS = ClientManager("ws")


class Server:

    """A game server.  The beating heart of the MUD."""

    def __init__(self):
        self._pid = None
        self._messages = get_pubsub()
        self._store = PickleStore("server")
        self._reloading = False

    def __repr__(self):
        return "Server<pid:{}>".format(self._pid)

    def _handle_msg(self, msg):
        if msg["channel"] == "server-reboot":
            target_pid = int(msg["data"])
            if target_pid == self._pid:
                raise ServerReboot
        elif msg["channel"] == "server-reload":
            target_pid, source_pid = map(int, msg["data"].split(","))
            if target_pid == self._pid:
                # We received a reload command from a new process.
                raise ServerReload(new_pid=source_pid)
        elif msg["channel"] == "server-shutdown":
            target_pid = int(msg["data"])
            if target_pid == self._pid:
                raise ServerShutdown

    def boot(self, reload_from=None):

        """Initialize and boot up the MUD server.

        Doesn't start looping until loop is called.

        :param int reload_from: The PID of an existing server process that this
                                server should request a state from
        :returns None:

        """
        with EVENTS.fire("server_init", no_pre=True):
            log.debug("Initializing server process %s.", self._pid)

        contrib_modules = settings.CONTRIB_MODULES
        if CLI.args.contrib:
            for module_name in CLI.args.contrib:
                contrib_modules.append(".contrib.{}".format(module_name))
        if contrib_modules:
            for module in contrib_modules:
                log.info("Loading '%s' module.", module.lstrip("."))
                import_module(module, BASE_PACKAGE)

        game_modules = settings.GAME_MODULES
        if CLI.args.game:
            for module_name in CLI.args.game:
                game_modules.append(".game.{}".format(module_name))
        if game_modules:
            for module in game_modules:
                log.info("Loading '%s' module.", module.lstrip("."))
                import_module(module, BASE_PACKAGE)

        # Parse command-line arguments again to account for anything that
        # contrib modules might have added.  From this point, any
        # unrecognized options or arguments will cause an error.
        CLI.parse()

        with EVENTS.fire("server_boot"):
            log.info("Booting server.")
            # Subscribe to Redis channels.
            self._messages.psubscribe("server-*")
            STORES.initialize()

        log.info("Server boot complete.")

        if reload_from:
            self._reloading = True
            BROKER.publish("server-reload",
                           "{},{}".format(reload_from, self._pid))
            # Wait until the other process is done saving a game state.
            while True:
                if self._store.has("state"):
                    break
                sleep(0.1)

        if self._store.has("state"):
            self.load_state()
            self._store.delete("state")
            self._store.commit()

        if reload_from:
            log.debug("Reload complete for process %s.", self._pid)
            BROKER.publish("server-reload-complete", self._pid)
            self._reloading = False

        BROKER.publish("server-boot-complete", self._pid)

    def loop(self):
        """Start the main server loop and loop until stopped."""
        try:
            while True:
                # First check for messages.
                msg = self._messages.get_message()
                while msg:
                    self._handle_msg(msg)
                    msg = self._messages.get_message()
                # Then do the main game logic.
                with EVENTS.fire("server_loop"):
                    TIMERS.pulse()  # Pulse each timer once.
                    for clients in (TEL_CLIENTS, WS_CLIENTS):
                        clients.check_connections()
                    SESSIONS.poll()  # Process queued IO.
                    for clients in (TEL_CLIENTS, WS_CLIENTS):
                        clients.poll()  # Check for new IO.
                    SESSIONS.prune()  # Clean up closed/dead sessions.
                # Any thing you want polled or updated should be done before
                # this point so that it is considered in the pulse delay.
                TIMERS.sleep_excess()  # Wait until the next pulse is ready.
        except KeyboardInterrupt:
            log.info("Received keyboard interrupt, stopping.")
        except ServerShutdown:
            log.info("Received server shutdown.")
        except ServerReboot:
            log.info("Received server reboot.")
        except ServerReload as exc:
            log.info("Reloading server.")
            self._messages.subscribe("server-reload-complete")
            self._reloading = True
            # Do one last session and client poll to clear the output queues.
            EVENTS.fire("server_reload", no_post=True).now()
            SESSIONS.poll(output_only=True)
            for clients in (TEL_CLIENTS, WS_CLIENTS):
                clients.poll()
            SESSIONS.prune()
            # Save the state data for the new process to resume from.
            self.save_state()
            # Wait for the new process to pick up the state.
            while True:
                msg = self._messages.get_message()
                if (msg and msg["type"] == "message" and
                        msg["channel"] == "server-reload-complete"):
                    pid = int(msg["data"])
                    if pid == exc.new_pid:
                        break
                sleep(0.1)
        finally:
            if not self._reloading:
                with EVENTS.fire("server_shutdown", no_post=True):
                    ENTITIES.save()
                    STORES.commit()
                    log.info("Server shutdown complete.")
                    BROKER.publish("server-shutdown-complete", self._pid)

    def shutdown(self):
        """Shutdown the server."""
        raise ServerShutdown

    def reboot(self):
        """Reboot the server."""
        raise ServerReboot

    def reload(self):
        """Request a reload from the nanny process."""
        BROKER.publish("server-reload-request", self._pid)

    def save_state(self):
        """Dump a serialized server state to file.

        This function just dumps a state dict into a pickle file, all the
        actual data processing and sanitizing should be done by individual
        modules post-hooking the server_save_state event; each module should
        add any data they want saved to the shared state dict before it is
        serialized.

        :returns None:

        """
        if self._store.has("state"):
            raise KeyError("a server state file already exists")
        log.info("Starting game state save.")
        ENTITIES.save()
        STORES.commit()
        state = {}
        with EVENTS.fire("server_save_state", state):
            self._store.put("state", state)
            self._store.commit()
        log.info("Game state save successful.")

    def load_state(self):
        """Load a serialized server state from file.

        This function just reads a pickle file into a state dict, all the
        actual data processing and sanitizing should be done by individual
        modules post-hooking the server_load_state event; each module should
        pull any data they want loaded from the shared state dict after it is
        deserialized.

        :returns None:

        """
        if not self._store.has("state"):
            raise KeyError("no server state file exists")
        log.info("Starting game state load.")
        state = self._store.get("state")
        EVENTS.fire("server_load_state", state).now()
        log.info("Game state load successful.")


SERVER = Server()


@EVENTS.hook("client_connected")
def _hook_client_connected(client):
    session = SESSIONS.create(client)
    with EVENTS.fire("session_started", session):
        session.send(SESSIONS.connect_greeting)


@EVENTS.hook("session_started")
def _hook_session_started(session):
    session.menu = ConnectMenu


@MENUS.register
class ConnectMenu(Menu):

    """A menu for new connections."""

    title = None
    ordering = Menu.ORDER_BY_ADDED


@ConnectMenu.add_entry("L", "Login")
def _connect_menu_login(session):

    def _success(_session, account):
        if account.options.reader or account.options.reader is Unset:
            _session.send(SESSIONS.login_greeting_reader)
        else:
            _session.send(SESSIONS.login_greeting_ascii)
        _session.account = account
        account.login(session)
        _session.menu = AccountMenu

    def _fail(_session, account):
        if isinstance(account, str):
            account = joins("unknown account:", account)
        _session.close("^RBad account name or password.^~",
                       log_msg=joins(session, " failed to log into ", account,
                                     ".", sep=""))

    authenticate_account(session, _success, _fail)


@ConnectMenu.add_entry("C", "Create account")
def _connect_menu_create_account(session):
    def _callback(_session, account):
        _session.send("\n^WWelcome ", account.name, "!^~", sep="")
        _session.account = account
        _session.menu = AccountMenu
    create_account(session, _callback)


@ConnectMenu.add_entry("Q", "Quit")
def _connect_menu_quit(session):
    session.close("Okay, goodbye!",
                  log_msg=joins(session, "has quit."))


@ConnectMenu.add_entry("?", "Help")
def _connect_menu_help(session):
    session.send("No help yet, sorry.")


if settings.FORCE_GC_COLLECT:
    TIMERS.create("1m", "gc_collect", repeat=-1, callback=collect)


@TIMERS.create("3m", "save_and_commit", repeat=-1)
def _save_and_commit():
    ENTITIES.save()
    STORES.commit()


def _get_announce_sessions():
    return (session for session in SESSIONS.all()
            if session.active and session.shell and
            session.shell.state >= const.STATE_PLAYING)


ANNOUNCE = Channel("^Y[ANNOUNCE]^W {msg}^~",
                   members=_get_announce_sessions)
CHANNELS.register("announce", ANNOUNCE)
