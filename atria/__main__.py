# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from multiprocessing import Process, Queue, Value
from time import sleep

import redis

# Note: Any modules imported here are not reloadable by the game server,
# you'll need to do a full reboot to reload changes to them.
from . import __version__, settings
from .core.logs import get_logger
from .libs.miniboa import TelnetServer


log = get_logger("main")


socket_queue = Queue()
rdb = redis.StrictRedis(decode_responses=True)
channels = rdb.pubsub(ignore_subscribe_messages=True)
servers = {}
listener = None


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

    @staticmethod
    def _start(pid, _socket_queue, reload_from=None):
        from .core.server import SERVER
        # Wait for our pid.
        while not pid.value:  # pragma: no cover
            continue
        SERVER._pid = pid.value
        SERVER.boot(_socket_queue, reload_from)
        SERVER.loop()

    def start(self, reload_from=None):
        """Start this server process.

        :param int reload_from: Optional, the PID of a running game server
                                process that this process should reload from
        :returns None:

        """
        assert not self._process, "server instance already started"
        pid = Value("i")
        self._process = Process(target=self._start,
                                args=(pid, socket_queue),
                                kwargs={"reload_from": reload_from})
        self._process.start()
        pid.value = self._process.pid


def _on_connect(new_socket, addr_port):  # pragma: no cover
    socket_queue.put((new_socket, addr_port))


def _handle_reload_request(msg):
    pid = int(msg["data"])
    if pid not in servers:  # pragma: no cover
        # There may be more than one nanny process running.
        return
    log.info("Received reload request from process %s.", pid)
    new_server = ServerProcess()
    listener.on_connect = _on_connect
    new_server.start(reload_from=pid)
    servers[new_server.pid] = new_server


def main():
    """Start the first server process and listen for sockets."""
    global listener
    log.info("%s %s.", settings.MUD_NAME_FULL, __version__)
    listener = TelnetServer(address=settings.BIND_ADDRESS,
                            port=settings.BIND_PORT,
                            timeout=0,
                            create_client=False)
    channels.subscribe(**{"server-reload-request": _handle_reload_request})
    server = ServerProcess()
    listener.on_connect = _on_connect
    server.start()
    servers[server.pid] = server
    try:
        while True:
            dead_servers = []
            for server in servers.values():
                if not server.alive:
                    log.info("Process %s finished with code %s.",
                              server.pid, server.exit_code)
                    dead_servers.append(server)
            for server in dead_servers:
                del servers[server.pid]
            if not servers:
                log.info("No servers running, goodbye.")
                break
            listener.poll()
            channels.get_message()
            sleep(0.1)
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        listener.stop()
        channels.unsubscribe()  # pragma: no cover


if __name__ == "__main__":
    main()
