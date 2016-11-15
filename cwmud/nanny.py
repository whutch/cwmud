# -*- coding: utf-8 -*-
"""A "nanny" process that manages individual server processes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from multiprocessing import Process, Value
from time import sleep

# Note: Any modules imported here are not reloadable by the game server,
# you'll need to do a full reboot to reload changes to them.
from . import __version__, settings
from .core.cli import CLI
from .core.logs import get_logger
from .core.messages import get_pubsub


log = get_logger("main")


messages = get_pubsub()
servers = {}


class ServerProcess:

    """A game server process."""

    def __init__(self):
        self._process = None

    @property
    def pid(self):
        """Return the PID of this game server process."""
        return self._process.pid

    @property
    def exit_code(self):
        """Return the exit code of this process."""
        return self._process.exitcode

    @property
    def alive(self):
        """Return whether this process is alive."""
        return self._process.is_alive()

    def start(self, reload_from=None):
        """Start this server process.

        :param int reload_from: Optional, the PID of a running game server
                                process that this process should reload from
        :returns None:

        """
        assert not self._process, "server instance already started"
        pid = Value("i")
        self._process = Process(target=_start_server,
                                args=(pid,),
                                kwargs={"reload_from": reload_from})
        self._process.start()
        pid.value = self._process.pid


def _start_server(pid, reload_from=None):
    from .core.server import SERVER
    # Wait for our pid.
    while not pid.value:  # pragma: no cover
        continue
    SERVER._pid = pid.value
    SERVER.boot(reload_from)
    SERVER.loop()


def _start_telnet_server():
    from .core.protocols.telnet import TelnetServer
    server = TelnetServer()
    server.serve()


def _start_websocket_server():
    from .core.protocols.websockets import WebSocketServer
    server = WebSocketServer()
    server.serve()


def _handle_reload_request(msg):
    pid = int(msg["data"])
    if pid not in servers:  # pragma: no cover
        # There may be more than one nanny process running.
        return
    log.info("Received reload request from process %s.", pid)
    new_server = ServerProcess()
    new_server.start(reload_from=pid)
    servers[new_server.pid] = new_server


def start_listeners():
    """Start the listener servers."""
    listeners = []
    telnet_server = Process(target=_start_telnet_server)
    telnet_server.daemon = True
    telnet_server.start()
    listeners.append(telnet_server)
    if CLI.args.ws:
        websocket_server = Process(target=_start_websocket_server)
        websocket_server.daemon = True
        websocket_server.start()
        listeners.append(websocket_server)
    return listeners


def start_nanny():
    """Start the nanny process and listen for sockets."""
    log.info("Starting %s %s.", settings.MUD_NAME_FULL, __version__)
    messages.subscribe(**{"server-reload-request": _handle_reload_request})
    # Start a MUD server.
    server = ServerProcess()
    server.start()
    servers[server.pid] = server
    try:
        while True:
            dead_servers = []
            for server in servers.values():
                if not server.alive:
                    log.debug("Process %s finished with code %s.",
                              server.pid, server.exit_code)
                    dead_servers.append(server)
            for server in dead_servers:
                del servers[server.pid]
            if not servers:
                log.info("No servers running, goodbye.")
                break
            messages.get_message()
            sleep(0.25)
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        messages.unsubscribe()  # pragma: no cover
