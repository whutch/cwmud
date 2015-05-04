# -*- coding: utf-8 -*-
"""Server initialization and loop logic."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from time import sleep

import redis

from .. import settings
from ..libs.miniboa import TelnetClient
from .accounts import AccountMenu, authenticate_account, create_account
from .entities import ENTITIES, Unset
from .events import EVENTS
from .logs import get_logger
from .menus import Menu, MENUS
from .net import CLIENTS
from .pickle import PickleStore
from .sessions import SESSIONS
from .storage import STORES
from .timing import TIMERS
from .utils.exceptions import ServerReboot, ServerReload, ServerShutdown
from .utils.funcs import joins


log = get_logger("server")


class Server:

    """A game server.  The beating heart of the MUD."""

    def __init__(self):
        self._socket_queue = None
        self._pid = None
        self._rdb = redis.StrictRedis(decode_responses=True)
        self._channels = self._rdb.pubsub(ignore_subscribe_messages=True)
        self._store = PickleStore("server")
        self._reloading = False

    def __repr__(self):
        return "Server<pid:{}>".format(self._pid)

    @staticmethod
    def _client_connected(client):
        with EVENTS.fire("client_connected", client, no_pre=True):
            log.info("Incoming connection from %s.", client.addrport())

    @staticmethod
    def _client_disconnected(client):
        with EVENTS.fire("client_disconnected", client, no_pre=True):
            log.info("Lost connection from %s.", client.addrport())

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

    # noinspection PyProtectedMember
    def _check_new_sockets(self):
        """Check the socket queue for new sockets that need clients."""
        if not self._socket_queue:
            return
        while not self._socket_queue.empty():
            socket, addr_port = self._socket_queue.get()
            client = TelnetClient(socket, addr_port)
            # noinspection PyProtectedMember
            CLIENTS._server.clients[client.fileno] = client
            if not self._reloading:
                self._client_connected(client)
            else:
                log.info("Recovering connection from %s.", client.addrport())

    def boot(self, socket_queue, reload_from=None):

        """Initialize and boot up the MUD server.

        Doesn't start looping until loop is called.

        :param multiprocessing.Queue socket_queue: A queue that will be fed
                                                   sockets by the nanny process
        :param int reload_from: The PID of an existing server process that this
                                server should request a state from
        :returns None:

        """
        self._socket_queue = socket_queue

        with EVENTS.fire("server_init", no_pre=True):
            log.info("Initializing server process %s.", self._pid)

        with EVENTS.fire("server_boot"):
            log.info("Booting server.")
            # Subscribe to Redis channels.
            self._channels.psubscribe("server-*")

        CLIENTS.listen(settings.BIND_ADDRESS,
                       settings.BIND_PORT,
                       self._client_connected,
                       self._client_disconnected,
                       server_socket=0)

        if reload_from:
            self._reloading = True
            self._rdb.publish("server-reload",
                              "{},{}".format(reload_from, self._pid))
            # Wait until the other process is done saving a game state.
            while True:
                if self._store.has("state"):
                    break
                sleep(0.1)
            # Pick up all the sockets from the socket queue.
            self._check_new_sockets()

        if self._store.has("state"):
            self.load_state()
            self._store.delete("state")
            self._store.commit()

        if reload_from:
            log.info("Reload complete for process %s.", self._pid)
            self._rdb.publish("server-reload-complete", self._pid)
            self._reloading = False

        self._rdb.publish("server-boot-complete", self._pid)

    def loop(self):
        """Start the main server loop and loop until stopped."""
        try:
            while True:
                # First check for messages.
                msg = self._channels.get_message()
                while msg:
                    self._handle_msg(msg)
                    msg = self._channels.get_message()
                # Then do the main game logic.
                with EVENTS.fire("server_loop"):
                    TIMERS.pulse()  # Pulse each timer once.
                    self._check_new_sockets()
                    SESSIONS.poll()  # Process queued IO.
                    CLIENTS.poll()  # Check for new IO.
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
            self._channels.subscribe("server-reload-complete")
            self._reloading = True
            # Do one last session and client poll to clear the output queues.
            SESSIONS.poll(output_only=True)
            CLIENTS.poll()
            SESSIONS.prune()
            # Save the state data for the new process to resume from.
            self.save_state()
            # Dump all the sockets back into the socket queue.
            for client in CLIENTS.clients.values():
                socket_data = (client.sock, (client.address, client.port))
                self._socket_queue.put(socket_data)
            # Wait for the new process to pick up the state.
            while True:
                msg = self._channels.get_message()
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
                    self._rdb.publish("server-shutdown-complete", self._pid)

    def reload(self):
        """Request a reload from the nanny process."""
        self._rdb.publish("server-reload-request", self._pid)

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
        session.menu = ConnectMenu


@EVENTS.hook("client_disconnected")
def _hook_client_disconnected(client):
    session = SESSIONS.find_by_client(client)
    if session:
        session._socket = None


@MENUS.register
class ConnectMenu(Menu):

    """A menu for new connections."""

    title = None
    ordering = Menu.ORDER_BY_ADDED


@ConnectMenu.add_entry("L", "Login")
def _connect_menu_login(session):

    def _success(_session, account):
        with EVENTS.fire("account_login", account):
            if account.options.reader or account.options.reader is Unset:
                _session.send(SESSIONS.login_greeting_reader)
            else:
                _session.send(SESSIONS.login_greeting_ascii)
            _session.account = account
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
    import gc
    TIMERS.create("1m", "gc_collect", repeat=-1, callback=gc.collect)


@TIMERS.create("3m", "save_and_commit", repeat=-1)
def _save_and_commit():
    ENTITIES.save()
    STORES.commit()
