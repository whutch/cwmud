# -*- coding: utf-8 -*-
"""Session management and client IO."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import deque
from os.path import exists, join

from .. import __version__, settings
from ..libs.miniboa import ANSI_CODES
from . import const
from .accounts import Account
from .characters import Character
from .events import EVENTS
from .logs import get_logger
from .menus import Menu
from .shells import Shell
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins
from .utils.mixins import HasFlags


log = get_logger("sessions")


class SessionManager:

    """A manager for client sessions."""

    def __init__(self):
        """Create a new session manager."""
        self.connect_greeting = "You're connected to {}, v{}.".format(
            settings.MUD_NAME_FULL, __version__)
        self.login_greeting_reader = "\nWelcome back!"
        self.login_greeting_ascii = self.login_greeting_reader
        self._sessions = {}

    def find_by_port(self, port):
        """Find a session by its port.

        :param int port: The port to search for
        :returns Session: A matching session or None

        """
        return self._sessions.get(port)

    def find_by_client(self, client):
        """Find a session by its client.

        :param miniboa.TelnetClient client: The client to search for
        :returns Session: A matching session or None

        """
        for session in self._sessions.values():
            # noinspection PyProtectedMember
            if session._client is client:
                return session

    def create(self, client, shell=None):
        """Create a new session tied to the given client.

        :param miniboa.TelnetClient client: The client to tie to the session
        :param Shell shell: Optional, a shell for the session
        :returns Session: The new session
        :raises AlreadyExists: If a session with that client already exists

        """
        if self.find_by_client(client):
            raise AlreadyExists(client, self.find_by_client(client))
        session = Session(client, shell)
        self._sessions[session.port] = session
        return session

    def poll(self, output_only=False):
        """Poll all sessions for queued IO.

        :param bool output_only: Whether to only process the output queue
                                 (this allows you to call poll from inside a
                                 command without triggering an infinite loop)
        :returns None:

        """
        for session in self._sessions.values():
            session.poll(output_only)

    def prune(self):
        """Clean up closed or dead sessions."""
        close = []
        for port, session in self._sessions.items():
            if not session.active:
                close.append(port)
        for port in close:
            del self._sessions[port]

    def all(self):
        """Return an iterator for all sessions."""
        return self._sessions.values()


class Session(HasFlags):

    """A session, sending and receiving data through a client."""

    def __init__(self, client, shell=None):
        """Create a new session tied to a client.

        Don't do this yourself, call SessionManager.create instead.

        """
        super().__init__()
        self._output_queue = deque()
        self._request_queue = deque()
        self._menu = None
        self._shell = None
        self._account = None
        self._char = None
        self._client = client
        if shell:
            self.shell = shell
        # Display options
        self.width = 80
        self._client.use_ansi = False

    def __del__(self):
        self._close()

    def __repr__(self):
        return joins("Session<", self.host, ":", self.port, ">", sep="")

    @property
    def active(self):
        """Return whether this session is still active."""
        return (not self.flags.has_any("closed", "dead") and
                self._client and self._client.active)

    @property
    def host(self):
        """Return the address this session is connected from."""
        return self._client.host

    @property
    def port(self):
        """Return the port this session is connected through."""
        return self._client.port

    @property
    def client(self):
        """Return the client for this session."""
        return self._client

    @property
    def menu(self):
        """Return the current menu for this session."""
        return self._menu

    @menu.setter
    def menu(self, new_menu):
        """Set the current menu for this session.

        :param menus.Menu new_menu: The menu to assign to this session
                                    (class or instance)
        :returns None:
        :raises TypeError: If `new_menu` is neither a subclass nor
                           an instance of Menu
        :raises ValueError: If `new_menu` is a Menu instance and its assigned
                            session is not this session

        """
        if new_menu is None:
            self._menu = None
        else:
            if isinstance(new_menu, type) and issubclass(new_menu, Menu):
                new_menu = new_menu(self)
            elif not isinstance(new_menu, Menu):
                raise TypeError("can only set session menu to a subclass or"
                                " instance of Menu")
            elif new_menu.session is not self:
                raise ValueError("cannot set session menu to menu instance"
                                 " that isn't tied to that session")
            self._menu = new_menu
            new_menu.display()

    @property
    def shell(self):
        """Return the current shell for this session."""
        return self._shell

    @shell.setter
    def shell(self, new_shell):
        """Set the current shell for this session.

        :param shells.Shell new_shell: The shell to assign to this session
                                       (class or instance)
        :returns None:
        :raises TypeError: If `new_shell` is neither a subclass nor
                           an instance of Shell

        """
        if new_shell is None:
            self._shell = None
        else:
            if isinstance(new_shell, type) and issubclass(new_shell, Shell):
                new_shell = new_shell()
            elif not isinstance(new_shell, Shell):
                raise TypeError("can only set session shell to a subclass or"
                                " instance of Shell")
            self._shell = new_shell
            # The order of these is important, as assigning the shell's
            # session will call its init() method.
            new_shell.session = self

    @property
    def account(self):
        """Return the current account for this session."""
        return self._account

    @account.setter
    def account(self, new_account):
        """Set the current account for this session.

        :param accounts.Account new_account: The account to assign
        :returns None:
        :raises TypeError: If `new_account` is not an instance of Account

        """
        if new_account is None:
            self._account = None
        else:
            if not isinstance(new_account, Account):
                raise TypeError("argument must be an Account instance")
            self._account = new_account
            new_account.session = self
            # Update any session settings that derive from account options.
            if new_account.options.width:
                self.width = new_account.options.width
            self.color = bool(new_account.options.color)

    @property
    def char(self):
        """Return the current character for this session."""
        return self._char

    @char.setter
    def char(self, new_char):
        """Set the current character for this session.

        :param characters.Character new_char: The character to assign
        :return None:

        """
        if new_char is None:
            self._char = None
        else:
            if not isinstance(new_char, Character):
                raise TypeError("argument must be a Character instance")
            self._char = new_char
            new_char.session = self

    @property
    def color(self):
        """Return whether this session is using color."""
        return self._client.use_ansi

    @color.setter
    def color(self, value):
        """Set whether this session is using color.

        :param bool value: Whether this session should use color or not
        :returns None:

        """
        self._client.use_ansi = bool(value)

    @classmethod
    def wrap_to_width(cls, text, width=80, parse_codes=True):
        """Wrap text to a given width.

        If `parse_codes` is True, the parser will count ^^ as a single
        character and won't count any other valid Miniboa formatting codes
        as characters when determining width.

        I haven't bothered with non-displaying characters like \b or \0, or
        with other whitespace characters like \t, \f, or \v, so including any
        of those will throw off the count and/or mess up the text.

        :param str text: The text to be wrapped
        :param int width: The target width to wrap the text around
        :param bool parse_codes: Whether the parser should check for Miniboa
                                 formatting codes with counting width
        :returns list: A list of wrapped strings

        """
        length = len(text)
        index = 0
        count = 0
        space = -1
        while index < length and count < width:
            if parse_codes and text[index] == "^":
                if text[index:index + 2] in ANSI_CODES:
                    index += 1
                elif text[index:index + 2] == "^^":
                    index += 1
                    count += 1
                else:
                    count += 1
            else:
                if text[index] == " ":
                    space = index
                count += 1
            index += 1
        stop = space if space > -1 else index
        if index == length:
            # End of the line, send everything.
            return [text]
        else:
            # We've hit this session's line width, send up to the last
            # space if there was one and then start over from there.
            wrapped = [text[:stop]]
            wrapped.extend(cls.wrap_to_width(text[stop + 1:]))
            return wrapped

    def _check_idle(self):
        """Check if this session is idle."""
        idle = self._client.get_idle_time()
        if settings.IDLE_TIME and idle >= settings.IDLE_TIME:
            if ((settings.IDLE_TIME_MAX and idle >= settings.IDLE_TIME_MAX) or
                    not self._shell or
                    self._shell.state < const.STATE_PLAYING):
                # They've been idle long enough, dump them.  If they haven't
                # even logged in yet, don't wait for the max idle time.
                if (self.account and
                        self.account.trust >= const.TRUST_BUILDER):
                    return
                self.close("^RDisconnecting due to inactivity. Goodbye!^~",
                           log_msg=joins("Disconnecting idle ", self,
                                         ".", sep=""))
            elif "idle" not in self.flags:
                with EVENTS.fire("session_idle"):
                    log.info("%s is now idle.", self)
                    self.send("You are whisked away into the void.")
                    self.flags.add("idle")
        elif "idle" in self.flags:
            # They came back, huzzah.
            with EVENTS.fire("session_idle_return"):
                log.info("%s is no longer idle.", self)
                self.send("You have returned from the void.")
                self.flags.drop("idle")

    def _parse_input(self, data):
        """Process input from the client.

        :param str data: The data to be processed
        :returns None:

        """
        if not data:
            # They just hit enter, let the prompt repeat itself.
            return
        if self._request_queue:
            if self._request_queue[0].resolve(data):
                self._request_queue.popleft()
        elif self._menu:
            self._menu.parse(data)
        elif self._shell:
            self._shell.parse(data)
        else:
            log.warning("Input not handled for %s: '%s'!", self, data)

    def _get_prompt(self):
        """Generate the current prompt for this session.

        :returns str: The generated prompt

        """
        if self._request_queue:
            return self._request_queue[0].get_prompt()
        elif self._menu:
            return self._menu.get_prompt()
        elif self._shell:
            return self._shell.get_prompt()
        else:
            return "^y>^~ "

    def send(self, data, *more, sep=" ", end="\n"):
        """Send text to the client tied to this session.

        The resulting output will not be sent immediately, but will be put
        in a queue to be sent during its next poll.

        `data` and all members of `more` will be converted to strings
        and joined together by `sep` via the joins function.

        :param any data: An initial chunk of data
        :param any more: Optional, any additional data to send
        :param str sep: Optional, a separator to join the resulting output by
        :param str end: Optional, a terminator appended to the resulting output
        :returns None:

        """
        self._output_queue.append(joins(data, *more, sep=sep) + end)

    def _send(self, data):
        """Put data in the client's output buffer to be sent next socket poll.

        The given data will be processed for any necessary text formatting
        prior to sending.

        :param str data: The data to send to the client
        :returns None:

        """
        lines = data.split("\n")
        formatted = []
        for line in lines:
            if line:
                formatted.extend(self.wrap_to_width(line, self.width))
            else:
                formatted.append("")
        self._client.send("\n".join(formatted))

    def poll(self, output_only=False):
        """Check the status of this session and process any queued IO.

        :param bool output_only: Whether to only process the output queue
                                 (this allows you to call poll from inside a
                                 command without triggering an infinite loop)
        :returns None:

        """
        # Do an initial state check.
        if (("close" in self.flags or not self.active) and
                "closed" not in self.flags and not output_only):
            with EVENTS.fire("session_ended", self):
                # Hooks to this event cannot send any output to the client,
                # they've already had their last poll.
                self.flags.drop("close")
                self._close()
                self.flags.add("closed")
        # If they're still around, handle their business.
        if self._client.active:
            if not output_only and self.active:
                self._check_idle()
            data = None
            if not output_only:
                # Process input through the command queue.
                if self._client.command_pending and self.active:
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
                self._send(output)
                self._output_queue.clear()
            # Send them a prompt if there was any input or output.
            if ((data is not None or output is not None) and self.active and
                    "close" not in self.flags):
                self._send(joins("\n", self._get_prompt(), sep=""))

    def _close(self):
        """Really close a session's socket."""
        if self.account:
            self.account.save()
        if self.char:
            self.char.save()
        if self._client:
            self._client.close()

    def close(self, reason, log_msg=""):
        """Close this session.

        The session will not be closed immediately, but will be flagged for
        closing at the end of its next poll.

        :param str reason: The reason this session is being closed, it will
                           be sent to the client prior to closing
        :param str log_msg: Optional, a custom log message for the closing
        :returns None:

        """
        if log_msg == "":
            log_msg = joins("Closing session ", self, ".", sep="")
        if log_msg:
            log.info(log_msg)
        self.send(reason)
        if self.char:
            self.char.suspend()
        if self.account:
            self.account.logout(self)
        self.flags.add("close")

    def request(self, request_class, callback, **options):
        """Request data from the client.

        :param requests.Request request_class: The request template
        :param callable callback: A callback for after the request resolves
        :param dict options: Keyword arguments passed to the request class
        :returns None:

        """
        other_requests = bool(self._request_queue)
        new_request = request_class(self, callback, **options)
        self._request_queue.append(new_request)
        if not other_requests:
            # Force a prompt this poll.
            self.send("", end="")

    def do(self, input_string):
        """Force a session to parse some input.

        :param str input_string: Input to pass to the character's shell
        :returns None:

        """
        self._parse_input(input_string)


# We create a global SessionManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more SessionManager instances if you like.
SESSIONS = SessionManager()


@EVENTS.hook("server_boot")
def _hook_server_boot():
    for name in ("login_greeting_reader", "login_greeting_ascii"):
        path = join(settings.DATA_DIR, name + ".txt")
        if exists(path):
            with open(path) as greeting_file:
                setattr(SESSIONS, name, greeting_file.read())


# noinspection PyProtectedMember
@EVENTS.hook("server_save_state", "sessions", pre=True)
def _hook_server_save_state(state):
    sessions = {}
    for session in SESSIONS._sessions.values():
        sessions[session.uid] = (
            session._output_queue,
            class_name(session.shell) if session.shell else None,
            class_name(session.menu) if session.menu else None,
            session.account.email if session.account else None,
            session.char.uid if session.char else None,
            session.width,
            session.color)
    state["sessions"] = sessions
