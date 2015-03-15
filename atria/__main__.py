# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from multiprocessing import Process, Queue
from time import sleep

import redis

# Note: Any modules imported here are not reloadable by the game server,
# you'll need to do a full reboot to reload changes to them.
from .libs.miniboa import TelnetServer
from . import __version__, settings
from .core.logs import get_logger


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

    @staticmethod
    def _start(_socket_queue, reload_from=None):
        from .core.server import SERVER
        SERVER.boot(_socket_queue, reload_from)
        SERVER.loop()

    def start(self, reload_from=None):
        """Start this server process.

        :param int reload_from: Optional, the PID of a running game server
                                process that this process should reload from

        """
        assert not self._process, "server instance already started"
        self._process = Process(target=self._start,
                                args=(socket_queue,),
                                kwargs={"reload_from": reload_from})
        self._process.start()


def _on_connect(new_socket, addr_port):
    socket_queue.put((new_socket, addr_port))


def _handle_reload_request(msg):
    pid = int(msg["data"])
    new_server = ServerProcess()
    listener.on_connect = _on_connect
    new_server.start(reload_from=pid)
    servers[new_server.pid] = new_server


def _handle_reload_complete(msg):
    if msg["type"] != "message":
        return
    pid = int(msg["data"])
    del servers[pid]


def main():
    """Start the first server process and listen for sockets."""
    global listener
    log.info("%s %s", settings.MUD_NAME_FULL, __version__)
    listener = TelnetServer(address=settings.BIND_ADDRESS,
                            port=settings.BIND_PORT,
                            timeout=0,
                            create_client=False)
    channels.subscribe(**{"reload-request": _handle_reload_request})
    try:
        server = ServerProcess()
        listener.on_connect = _on_connect
        server.start()
        servers[server.pid] = server
        while True:
            listener.poll()
            channels.get_message()
            sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
