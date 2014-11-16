# -*- coding: utf-8 -*-
"""Session management and client IO."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from collections import deque

from .. import settings
from .events import EVENTS
from .logs import get_logger
from .shells import SHELLS, STATES, Shell
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins
from .utils.mixins import HasFlags


log = get_logger("sessions")


class SessionManager:

    """A manager for client sessions."""

    def __init__(self):
        """Create a new session manager."""
        self.greeting = "Welcome!\n"
        self._sessions = []

    def find_by_client(self, client):
        """Find a session by its client.

        :param miniboa.TelnetClient client: The client to search for
        :returns _Session|None: A matching session or None

        """
        for session in self._sessions:
            # noinspection PyProtectedMember
            if session._client is client:
                return session

    def create(self, client, shell=None):
        """Create a new session tied to the given client.

        :param miniboa.TelnetClient client: The client to tie to the session
        :param Shell shell: Optional, a shell for the session
        :returns _Session: The new session
        :raises AlreadyExists: If a session with that client already exists

        """
        if self.find_by_client(client):
            raise AlreadyExists(client, self.find_by_client(client))
        session = _Session(client, shell)
        self._sessions.append(session)
        return session

    def poll(self):
        """Poll all sessions for queued IO."""
        for session in self._sessions:
            session.poll()

    def prune(self):
        """Clean up closed or dead sessions."""
        self._sessions = [session for session in self._sessions
                          if session.active]


class _Session(HasFlags):

    """A session, sending and receiving data through a client."""

    def __init__(self, client, shell=None):
        """Create a new session tied to a client.

        Don't do this yourself, call SessionManager.create instead.

        """
        super().__init__()
        self._address = client.addrport().rsplit(":", 1)[0]
        self._output_queue = deque()
        self._request_queue = deque()
        self._shell = None
        self._client = client
        if shell:
            self.shell = shell

    def __del__(self):
        if self._client:
            self._client.sock.close()
            self._client.active = False

    def __repr__(self):
        return joins("Session<", self._address, ">", sep="")

    @property
    def active(self):
        """Return whether this session is still active."""
        return (not self.flags.has_any("close", "closed", "dead")
                and self._client and self._client.active)

    @property
    def address(self):
        """Return the address this session is connected from."""
        return self._address

    @property
    def shell(self):
        """Return the current shell for this session."""
        return self._shell

    @shell.setter
    def shell(self, shell):
        """Set the current shell for this session.

        :param class|Shell|None shell: The shell to assign to this session
                                       (class or instance) or None
        :returns: None
        :raises TypeError: If `shell` is provided and is not either a
                           subclass of Shell or an instance of a subclass

        """
        if shell is None:
            self._shell = None
        else:
            if isinstance(shell, type) and issubclass(shell, Shell):
                shell = shell()
            elif not isinstance(shell, Shell):
                raise TypeError("argument must be shell class or instance")
            self._shell = shell
            # The order of these is important, as assigning the shell's
            # session will call its init() method.
            shell.session = self

    def _check_idle(self):
        """Check if this session is idle."""
        idle = self._client.idle()
        if idle >= settings.IDLE_TIME:
            if (idle >= settings.IDLE_TIME_MAX or
                    not self._shell or self._shell.state < STATES.playing):
                # They've been idle long enough, dump them. If they haven't
                # even logged in yet, don't wait for the max idle time.
                self.close("^RDisconnecting due to inactivity. Goodbye!^~",
                           log_msg=joins("Disconnecting idle", self))
            elif "idle" not in self.flags:
                with EVENTS.fire("session_idle"):
                    log.info("%s is now idle", self)
                    self.flags.add("idle")
        elif "idle" in self.flags:
            # They came back, huzzah.
            with EVENTS.fire("session_idle_return"):
                log.info("%s is no longer idle", self)
                self.flags.drop("idle")

    def _parse_input(self, data):
        """Process input from the client.

        :param str data: The data to be processed
        :returns: None

        """
        if self._shell:
            self._shell.parse(data)
        else:
            log.warn("Input not handled for %s: %s", self, data)

    def _get_prompt(self):
        """Generate the current prompt for this session.

        :returns str: The generated prompt

        """
        if self._shell:
            return self._shell.get_prompt()
        else:
            return "^y>^~ "

    def send(self, data, *more, sep=" ", end="\n"):
        """Send text to the client tied to this session.

        The resulting output will not be sent immediately, but will be put
        in a queue to be sent during its next poll.

        `message` and all members of `more` will be converted to strings
        and joined together by `sep` via the joins function.

        :param any data: An initial chunk of data
        :param any more: Optional, any additional data to send
        :param str sep: Optional, a separator to join the resulting output by
        :param str end: Optional, a terminator appended to the resulting output

        """
        self._output_queue.append(joins(data, *more, sep=sep) + end)

    def poll(self):
        """Check the status of this session and process any queued IO."""
        if self._client.active:
            if self.active:
                self._check_idle()
            # Process input through the command queue.
            data = None
            if self._client.cmd_ready and self.active:
                data = self._client.get_command()
                if data is not None:
                    self._parse_input(data)
            # Process output from the output queue.
            output = None
            if self._output_queue and self._client:
                # This can later be made more sophisticated with paged output,
                # width-reformatting, etc., but for now it's pretty simple.
                if data is None:
                    # We didn't get a command this poll, so we need to send
                    # them a newline before anything else.
                    self._output_queue.appendleft("\n")
                output = "".join(self._output_queue)
                self._client.send_cc(output)
                self._output_queue.clear()
            # Send them a prompt if there was any input or output.
            if (data is not None or output is not None) and self.active:
                self._client.send_cc(self._get_prompt())
        # All the IO is done, do a final state check.
        if not self.active and "closed" not in self.flags:
            with EVENTS.fire("session_ended", self):
                # Hooks to this event cannot send any output to the client,
                # this is its last poll.
                self.flags.drop("close")
                self.flags.add("closed")

    def close(self, reason, log_msg=""):
        """Close this session.

        The session will not be closed immediately, but will be flagged for
        closing at the end of its next poll.

        :param str reason: The reason this session is being closed, it will
                           be sent to the client prior to closing
        :param str log_msg: Optional, a custom log message for the closing

        """
        if not log_msg:
            log_msg = joins("Closing session", self)
        log.info(log_msg)
        self.send(reason)
        self.flags.add("close")


# We create a global SessionManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more SessionManager instances if you like.
SESSIONS = SessionManager()


# noinspection PyProtectedMember
@EVENTS.hook("server_save_state", "sessions", pre=True)
def _hook_server_save_state(state, pass_to_pid):
    sessions = []
    # If sockets won't be saved, there's no point in saving sessions
    if pass_to_pid is not None:
        for session in SESSIONS._sessions:
            sessions.append((session._client.fileno,
                             class_name(session.shell)))
    state["sessions"] = sessions


# noinspection PyProtectedMember
@EVENTS.hook("server_load_state", "sessions", after="clients")
def _hook_server_load_state(state):
    sessions = state["sessions"]
    clients = state["clients"]
    for socket_fileno, shell_name in sessions:
        if socket_fileno not in clients:
            # The client is gone, so no need for the session
            continue
        client = clients[socket_fileno]
        shell = SHELLS[shell_name]
        session = _Session(client, shell)
        SESSIONS._sessions.append(session)
