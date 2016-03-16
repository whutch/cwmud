# -*- coding: utf-8 -*- line endings: unix -*-
"""A bare-bones cross-platform Telnet server."""
# miniboa.py
# Copyright 2009 Jim Storch
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Changes made by pR0Ps.CM[at]gmail[dot]com on 18/07/2012
# -Updated for use with Python 3.x
# -Repackaged into a single file to simplify distribution
# -Other misc fixes and changes
# Report any bugs in this implementation to me (email above)

# Further changes made by Will Hutcheson (will@whutch.com)
# for the Clockwork MUD Server (https://github.com/whutch/cwmud)

import socket
import select
import sys
import re
import time

from ..core.logs import get_logger


logging = get_logger("miniboa")


# Telnet Notes
# ============
#
# (See RFC 854 for more information)
#
# Negotiating a Local Option
# --------------------------
#
# Side A begins with:
#
#    "IAC WILL/WONT XX"   Meaning "I would like to [use|not use] option XX."
#
# Side B replies with either:
#
#    "IAC DO XX"     Meaning "OK, you may use option XX."
#    "IAC DONT XX"   Meaning "No, you cannot use option XX."
#
#
# Negotiating a Remote Option
# ----------------------------
#
# Side A begins with:
#
#    "IAC DO/DONT XX"  Meaning "I would like YOU to [use|not use] option XX."
#
# Side B replies with either:
#
#    "IAC WILL XX"   Meaning "I will begin using option XX"
#    "IAC WONT XX"   Meaning "I will not begin using option XX"
#
#
# The syntax is designed so that if both parties receive simultaneous requests
# for the same option, each will see the other's request as a positive
# acknowledgement of it's own.
#
# If a party receives a request to enter a mode that it is already in, the
# request should not be acknowledged.


UNKNOWN = -1
# Cap sockets to 500 on Windows because WinSock can only process 512 at time
# Cap sockets to 1000 on Linux because you can only have 1024 file descriptors
MAX_CONNECTIONS = 500 if sys.platform == 'win32' else 1000
PARA_BREAK = re.compile(r"(\n\s*\n)", re.MULTILINE)

ANSI_CODES = {
    '^k': '\x1b[22;30m',  # black
    '^K': '\x1b[1;30m',  # bright black (grey)
    '^r': '\x1b[22;31m',  # red
    '^R': '\x1b[1;31m',  # bright red
    '^g': '\x1b[22;32m',  # green
    '^G': '\x1b[1;32m',  # bright green
    '^y': '\x1b[22;33m',  # yellow
    '^Y': '\x1b[1;33m',  # bright yellow
    '^b': '\x1b[22;34m',  # blue
    '^B': '\x1b[1;34m',  # bright blue
    '^m': '\x1b[22;35m',  # magenta
    '^M': '\x1b[1;35m',  # bright magenta
    '^c': '\x1b[22;36m',  # cyan
    '^C': '\x1b[1;36m',  # bright cyan
    '^w': '\x1b[22;37m',  # white
    '^W': '\x1b[1;37m',  # bright white
    '^0': '\x1b[40m',  # black background
    '^1': '\x1b[41m',  # red background
    '^2': '\x1b[42m',  # green background
    '^3': '\x1b[43m',  # yellow background
    '^4': '\x1b[44m',  # blue background
    '^5': '\x1b[45m',  # magenta background
    '^6': '\x1b[46m',  # cyan background
    '^d': '\x1b[39m',  # default (should be white on black)
    '^I': '\x1b[7m',  # inverse text on
    '^i': '\x1b[27m',  # inverse text off
    '^~': '\x1b[0m',  # reset all
    '^U': '\x1b[4m',  # underline on
    '^u': '\x1b[24m',  # underline off
    '^!': '\x1b[1m',  # bold on
    '^.': '\x1b[22m',  # bold off
    '^s': '\x1b[2J',  # clear screen
    '^l': '\x1b[2K',  # clear to end of line
}

# Telnet commands
SE = chr(240)  # End of sub-negotiation parameters
NOP = chr(241)  # No operation
DATMK = chr(242)  # Data stream portion of a sync.
BREAK = chr(243)  # NVT Character BRK
IP = chr(244)  # Interrupt Process
AO = chr(245)  # Abort Output
AYT = chr(246)  # Are you there
EC = chr(247)  # Erase Character
EL = chr(248)  # Erase Line
GA = chr(249)  # The Go Ahead Signal
SB = chr(250)  # Sub-option to follow
WILL = chr(251)  # Will; request or confirm option begin
WONT = chr(252)  # Wont; deny option request
DO = chr(253)  # Do = Request or confirm remote option
DONT = chr(254)  # Don't = Demand or confirm option halt
IAC = chr(255)  # Interpret as Command
SEND = chr(1)  # Sub-process negotiation SEND command
IS = chr(0)  # Sub-process negotiation IS command

# Telnet options
BINARY = chr(0)  # Transmit Binary
ECHO = chr(1)  # Echo characters back to sender
RECON = chr(2)  # Reconnection
SGA = chr(3)  # Suppress Go-Ahead
TTYPE = chr(24)  # Terminal Type
NAWS = chr(31)  # Negotiate About Window Size
LINEMODE = chr(34)  # Line Mode


_COMMAND_NAMES = {
    SE: "SE",
    NOP: "NOP",
    DATMK: "DATMK",
    BREAK: "BREAK",
    IP: "IP",
    AO: "AO",
    AYT: "AYT",
    EC: "EC",
    EL: "EL",
    GA: "GA",
    SB: "SB",
    WILL: "WILL",
    WONT: "WONT",
    DO: "DO",
    DONT: "DONT",
    IAC: "IAC",
    SEND: "SEND",
    IS: "IS",
}

_OPTION_NAMES = {
    BINARY: "BINARY",
    ECHO: "ECHO",
    RECON: "RECON",
    SGA: "SGA",
    TTYPE: "TTYPE",
    NAWS: "NAWS",
    LINEMODE: "LINEMODE",
}


class ConnectionLost(Exception):
    """Custom exception to signal a lost connection to the Telnet Server."""
    pass


def strip_caret_codes(text):
    """Strip out any caret codes from a string.

    :param str text: The text to strip the codes from
    :returns str: The clean text

    """
    text = text.replace('^^', '\x00')
    for token, foo in ANSI_CODES.items():
        text = text.replace(token, '')
    return text.replace('\x00', '^')


def colorize(text, ansi=True):
    """Replace tokens in a string with ANSI sequences, or strip them out.

    :param str text: The text to replace the tokens in
    :param bool ansi: Whether to colorize the string or strip it of tokens
    :returns str: The colorized text

    """
    if ansi:
        text = text.replace('^^', '\x00')
        for token, code in ANSI_CODES.items():
            text = text.replace(token, code)
        text = text.replace('\x00', '^')
    else:
        text = strip_caret_codes(text)
    return text


def word_wrap(text, columns=80, indent=4, padding=2):
    """Given a block of text, break it into a list of lines wrapped to length.

    :param str text: The text to wrap
    :param int columns: The number of columns to wrap the text to
    :param int indent: The number of spaces to indent additionally lines to
    :param int padding: The number of columns to pad each side with
    :returns list: A list of wrapped strings

    """
    paragraphs = PARA_BREAK.split(text)
    lines = []
    columns -= padding
    for para in paragraphs:
        if para.isspace():
            continue
        line = ' ' * indent
        for word in para.split():
            if (len(line) + 1 + len(word)) > columns:
                lines.append(line)
                line = ' ' * padding
                line += word
            else:
                line += ' ' + word
        if not line.isspace():
            lines.append(line)
    return lines


class TelnetOption(object):

    """Simple class used to track the status of an extended Telnet option."""

    def __init__(self):
        self.local_option = UNKNOWN     # Local state of an option
        self.remote_option = UNKNOWN    # Remote state of an option
        self.reply_pending = False      # Are we expecting a reply?


class TelnetClient(object):

    """A client connection via Telnet."""

    def __init__(self, sock, addr_tup):
        """Create a new client connection.

        :param socket.socket sock: The socket of the new connection
        :param tuple addr_tup: A tuple of (address, port number)

        """
        self.protocol = 'telnet'
        self.active = True  # Turns False when the connection is lost
        self.sock = sock  # The connection's socket
        self.fileno = sock.fileno()  # The socket's file descriptor
        self.address = addr_tup[0]  # The client's remote TCP/IP address
        self.port = addr_tup[1]  # The client's remote port
        self.terminal_type = 'ANSI'  # set via request_terminal_type()
        self.use_ansi = True
        self.columns = 80
        self.rows = 24
        self.send_pending = False
        self.send_buffer = ''
        self.recv_buffer = ''
        self.bytes_sent = 0
        self.bytes_received = 0
        self.cmd_ready = False
        self.command_list = []
        self.connect_time = time.time()
        self.last_input_time = time.time()
        self.line_mode = True

        # State variables for interpreting incoming telnet commands
        self.telnet_got_iac = False  # Are we inside an IAC sequence?
        self.telnet_got_cmd = None  # Did we get a telnet command?
        self.telnet_got_sb = False  # Are we inside a subnegotiation?
        self.telnet_opt_dict = {}  # Mapping for up to 256 TelnetOptions
        self.telnet_echo = False  # Echo input back to the client?
        self.telnet_echo_password = False  # Echo back '*' for passwords?
        self.telnet_sb_buffer = ''  # Buffer for sub-negotiations

    def __repr__(self):
        return "TelnetClient<{}:{}({})>".format(
            self.address, self.port, self.fileno)

    def get_command(self):
        """Get a line of text that was received from the client.

        The client's cmd_ready attribute will be true if lines are available.

        :returns str: The found command or None

        """
        cmd = None
        count = len(self.command_list)
        if count > 0:
            cmd = self.command_list.pop(0)
        # If that was the last line, turn off lines_pending
        if count == 1:
            self.cmd_ready = False
        return cmd

    def send(self, text):
        """Send raw text to the distant end.

        The text will be buffered and sent during the next server poll.

        :param str text: The text to send
        :returns None:

        """
        if text:
            self.send_buffer += text.replace('\n', '\r\n')
            self.send_pending = True

    def send_cc(self, text):
        """Send text with caret codes converted to ANSI codes.

        :param str text: The text to send
        :returns None:

        """
        self.send(colorize(text, self.use_ansi))

    def send_wrapped(self, text):
        """Send text padded and wrapped to the user's screen width.

        :param str text: The text to send
        :returns None:

        """
        lines = word_wrap(text, self.columns)
        for line in lines:
            self.send_cc(line + '\n')

    def deactivate(self):
        """Set the client to disconnect on the next server poll."""
        self.active = False

    def addrport(self):
        """Return the client's IP address and port number as a string.

        :returns str: A string in the format of "address:port"

        """
        return "{}:{}".format(self.address, self.port)

    def idle(self):
        """Return the client's idle time.

        Idle time is the number of seconds that have elapsed since the client
        last sent us some input.

        :returns float: The idle time, in seconds

        """
        return time.time() - self.last_input_time

    def duration(self):
        """Return the client's total connected time.

        :returns float: The connected time, in seconds

        """
        return time.time() - self.connect_time

    def request_do_sga(self):
        """Request client to Suppress Go-Ahead.

        See RFC 858.

        """
        self._iac_do(SGA)
        self._note_reply_pending(SGA, True)

    def request_will_echo(self):
        """Tell the client that we would like to echo their text.

        See RFC 857.

        """
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)
        self.telnet_echo = True

    def request_wont_echo(self):
        """Tell the client that we would like to stop echoing their text.

        See RFC 857.

        """
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)
        self.telnet_echo = False

    def password_mode_on(self):
        """Tell client we will echo (but don't) so passwords don't show."""
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)

    def password_mode_off(self):
        """Tell client we are done echoing (we lied) and show typing again."""
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)

    def request_naws(self):
        """Request to Negotiate About Window Size.

        See RFC 1073.

        """
        self._iac_do(NAWS)
        self._note_reply_pending(NAWS, True)

    def request_terminal_type(self):
        """Request the terminal type from the client.

        See RFC 779.

        """
        self._iac_do(TTYPE)
        self._note_reply_pending(TTYPE, True)

    def request_linemode_off(self):
        """Tell the client to disable line-mode."""
        self._iac_do(LINEMODE)
        self.send("{}{}{}{}{}{}{}".format(IAC, SB, LINEMODE,
                                          chr(1), chr(0), IAC, SE))
        self.line_mode = False

    def socket_send(self):
        """Send data to the client socket.

        Called by TelnetServer when there is data ready to send.

        """
        if len(self.send_buffer):
            try:
                # Convert to ANSI before sending.
                sent = self.sock.send(bytes(self.send_buffer, "cp1252"))
            except socket.error as err:
                logging.error("SEND error '{}' from {}".format(
                    err, self.addrport()))
                self.active = False
                return
            self.bytes_sent += sent
            self.send_buffer = self.send_buffer[sent:]
        else:
            self.send_pending = False

    def socket_recv(self):
        """Receive data from the client socket.

        Called by TelnetServer when there is data ready to receive.

        Since we were told that the client is ready to send data, if no data
        is received, we can assume their is a problem on the client end and
        they have or can be disconnected.

        :returns None:
        :raises ConnectionLost: If no data is received

        """
        try:
            # Encode received bytes in ANSI.
            data = str(self.sock.recv(2048), "cp1252")
        except socket.error as err:
            logging.error("RECEIVE socket error '{}' from {}".format(
                err, self.addrport()))
            raise ConnectionLost()
        # Did they close the connection?
        size = len(data)
        if size == 0:
            logging.debug("No data received, client closed connection")
            raise ConnectionLost()
        # Update some trackers.
        self.last_input_time = time.time()
        self.bytes_received += size
        # Test for telnet commands.
        for byte in data:
            self._iac_sniffer(byte)
        if self.line_mode:
            # Look for newline characters to get whole lines from the buffer.
            while True:
                mark = self.recv_buffer.find('\n')
                if mark == -1:
                    break
                cmd = self.recv_buffer[:mark].strip()
                self.command_list.append(cmd)
                self.cmd_ready = True
                self.recv_buffer = self.recv_buffer[mark + 1:]
        else:
            self.command_list.extend(self.recv_buffer)
            self.recv_buffer = ""

    def _recv_byte(self, byte):
        """Process receiving a single byte.

        Non-printable filtering currently disabled because it did not play
        well with extended character sets.

        :param str byte: The byte to buffer
        :returns None:

        """
        # Filter out non-printing characters.
        # if (byte >= ' ' and byte <= '~') or byte == '\n':
        if self.telnet_echo:
            self._echo_byte(byte)
        self.recv_buffer += byte

    def _echo_byte(self, byte):
        """Echo a character back to the client and convert LF into CR\LF."""
        if byte == '\n':
            self.send_buffer += '\r'
        if self.telnet_echo_password:
            self.send_buffer += '*'
        else:
            self.send_buffer += byte

    def _iac_sniffer(self, byte):
        """Check incoming data for Telnet IAC sequences.

        Passes the data, if any, with the IAC commands stripped
        to _recv_byte().

        :param str byte: The byte to check
        :returns None:

        """
        # Are we not currently in an IAC sequence coming from the client?
        if self.telnet_got_iac is False:
            if byte == IAC:
                # Well, we are now
                self.telnet_got_iac = True
                return
            # Are we currently in a sub-negotiation?
            elif self.telnet_got_sb is True:
                # Sanity check on length.
                if len(self.telnet_sb_buffer) < 64:
                    self.telnet_sb_buffer += byte
                else:
                    self.telnet_got_sb = False
                    self.telnet_sb_buffer = ""
                return
            else:
                # Just a normal NVT character
                self._recv_byte(byte)
                return
        # Byte handling when already in an IAC sequence sent from the client
        else:
            # Did we get sent a second IAC?
            if byte == IAC and self.telnet_got_sb is True:
                # Must be an escaped 255 (IAC + IAC)
                self.telnet_sb_buffer += byte
                self.telnet_got_iac = False
                return
            # Do we already have an IAC + CMD?
            elif self.telnet_got_cmd:
                # Yes, so handle the option
                self._three_byte_cmd(byte)
                return
            # We have IAC but no CMD
            else:
                # Is this the middle byte of a three-byte command?
                if byte == DO:
                    self.telnet_got_cmd = DO
                    return
                elif byte == DONT:
                    self.telnet_got_cmd = DONT
                    return
                elif byte == WILL:
                    self.telnet_got_cmd = WILL
                    return
                elif byte == WONT:
                    self.telnet_got_cmd = WONT
                    return
                else:
                    # Nope, must be a two-byte command
                    self._two_byte_cmd(byte)

    def _two_byte_cmd(self, cmd):
        """Handle incoming Telnet commands that are two bytes long.

        :param str cmd: The received command byte
        :returns None:

        """
        logging.debug("Got two byte cmd '{}'"
                      .format(_COMMAND_NAMES.get(cmd, "?")))
        if cmd == SB:
            # Begin capturing a sub-negotiation string
            self.telnet_got_sb = True
            self.telnet_sb_buffer = ''
        elif cmd == SE:
            # Stop capturing a sub-negotiation string
            self.telnet_got_sb = False
            self._sb_decoder()
        elif cmd == NOP:
            pass
        elif cmd == DATMK:
            pass
        elif cmd == IP:
            pass
        elif cmd == AO:
            pass
        elif cmd == AYT:
            pass
        elif cmd == EC:
            pass
        elif cmd == EL:
            pass
        elif cmd == GA:
            pass
        else:
            logging.warning("Send an invalid 2 byte command")
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """Handle incoming Telnet commands that are three bytes long.

        :param str option: The received option byte
        :returns None:

        """
        cmd = self.telnet_got_cmd
        logging.debug("Got three byte cmd {}:{}"
                      .format(_COMMAND_NAMES.get(cmd, "?"),
                              _OPTION_NAMES.get(option, "?")))
        # Incoming DO's and DONT's refer to the status of this end
        if cmd == DO:
            if option == BINARY or option == SGA or option == ECHO:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_local_option(option, True)
                elif (self._check_local_option(option) is False or
                        self._check_local_option(option) is UNKNOWN):
                    self._note_local_option(option, True)
                    self._iac_will(option)
                    # Just nod unless setting echo
                    if option == ECHO:
                        self.telnet_echo = True
            else:
                # All other options = Default to refusing once
                if self._check_local_option(option) is UNKNOWN:
                    self._note_local_option(option, False)
                    self._iac_wont(option)
        elif cmd == DONT:
            if option == BINARY or option == SGA or option == ECHO:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_local_option(option, False)
                elif (self._check_local_option(option) is True or
                        self._check_local_option(option) is UNKNOWN):
                    self._note_local_option(option, False)
                    self._iac_wont(option)
                    # Just nod unless setting echo
                    if option == ECHO:
                        self.telnet_echo = False
            else:
                # All other options = Default to ignoring
                pass
        # Incoming WILL's and WONT's refer to the status of the client
        elif cmd == WILL:
            if option == ECHO:
                # Nutjob client offering to echo the server...
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    # No no, bad client!
                    self._iac_dont(ECHO)
            elif option == NAWS or option == SGA:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_remote_option(option, True)
                elif (self._check_remote_option(option) is False or
                        self._check_remote_option(option) is UNKNOWN):
                    self._note_remote_option(option, True)
                    self._iac_do(option)
                    # Client should respond with SB (for NAWS)
            elif option == TTYPE:
                if self._check_reply_pending(TTYPE):
                    self._note_reply_pending(TTYPE, False)
                    self._note_remote_option(TTYPE, True)
                    # Tell them to send their terminal type
                    self.send("{}{}{}{}{}{}".format(IAC, SB, TTYPE,
                                                    SEND, IAC, SE))
                elif (self._check_remote_option(TTYPE) is False or
                        self._check_remote_option(TTYPE) is UNKNOWN):
                    self._note_remote_option(TTYPE, True)
                    self._iac_do(TTYPE)
        elif cmd == WONT:
            if option == ECHO:
                # Client states it wont echo us -- good,
                # they're not supposes to.
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    self._iac_dont(ECHO)
            elif option == SGA or option == TTYPE:
                if self._check_reply_pending(option):
                    self._note_reply_pending(option, False)
                    self._note_remote_option(option, False)
                elif (self._check_remote_option(option) is True or
                        self._check_remote_option(option) is UNKNOWN):
                    self._note_remote_option(option, False)
                    self._iac_dont(option)
                # Should TTYPE be below this?
            else:
                # All other options = Default to ignoring
                pass
        else:
            logging.warning("Send an invalid 3 byte command")
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _sb_decoder(self):
        """Figure out what to do with a received sub-negotiation block."""
        bloc = self.telnet_sb_buffer
        logging.debug("Got sub negotiation %s",
                      " ".join([str(ord(c)) for c in bloc]))
        if len(bloc) > 2:
            if bloc[0] == TTYPE and bloc[1] == IS:
                self.terminal_type = bloc[2:]
                logging.debug("Terminal type = '{}'"
                              .format(self.terminal_type))
            if bloc[0] == NAWS:
                if len(bloc) != 5:
                    logging.warning("Bad length on NAWS SB: " + str(len(bloc)))
                else:
                    self.columns = (256 * ord(bloc[1])) + ord(bloc[2])
                    self.rows = (256 * ord(bloc[3])) + ord(bloc[4])
                logging.info("Screen is {} x {}".format(self.columns,
                                                        self.rows))
            if bloc[0] == LINEMODE:
                if bloc[1] == chr(1):
                    if len(bloc) != 3:
                        logging.warning("Bad LINEMODE SB: %s",
                                        " ".join([str(ord(c))
                                                  for c in bloc[0:]]))
                    else:
                        self.line_mode = bool(ord(bloc[2]) & 1)
        self.telnet_sb_buffer = ''

    # Sometimes verbiage is tricky.  I use 'note' rather than 'set' here
    # because (to me) set infers something happened.

    def _check_local_option(self, option):
        """Test the status of local negotiated Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].local_option

    def _note_local_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].local_option = state

    def _check_remote_option(self, option):
        """Test the status of remote negotiated Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].remote_option

    def _note_remote_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].remote_option = state

    def _check_reply_pending(self, option):
        """Test the status of requested Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].reply_pending

    def _note_reply_pending(self, option, state):
        """Record the status of requested Telnet options."""
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].reply_pending = state

    def _iac_do(self, option):
        """Send a Telnet IAC "DO" sequence."""
        self.send("{}{}{}".format(IAC, DO, option))

    def _iac_dont(self, option):
        """Send a Telnet IAC "DONT" sequence."""
        self.send("{}{}{}".format(IAC, DONT, option))

    def _iac_will(self, option):
        """Send a Telnet IAC "WILL" sequence."""
        self.send("{}{}{}".format(IAC, WILL, option))

    def _iac_wont(self, option):
        """Send a Telnet IAC "WONT" sequence."""
        self.send("{}{}{}".format(IAC, WONT, option))


class TelnetServer(object):

    """A select-based Telnet server."""

    def __init__(self, port=23, address='', on_connect=None,
                 on_disconnect=None, max_connections=MAX_CONNECTIONS,
                 timeout=0.1, server_socket=None, create_client=True):
        """ Create a new Telnet server.

        :param int port: The port to listen for new connection on; on
                         UNIX-like platforms you made need root access to
                         use ports under 1025
        :param str address: The address of the LOCAL network interface to
                            bind the listening port to; you can usually leave
                            this blank unless you want to restrict traffic
                            to a specific network device
        :param callable on_connect: Callback for new telnet connections
        :param callable on_disconnect: Callback for lost telnet connections
        :param int max_connections: Maximum simultaneous connections the
                                    server will allow
        :param float timeout: Amount of time that the server will wait for
                              client input while polling
        :param socket server_socket: Optional, an existing server socket to use
        :param bool create_client: Whether to create new client instances or
                                   pass the incoming sockets directly to the
                                   on_connect callback

        """
        self.port = port
        self.address = address
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.max_connections = min(max_connections, MAX_CONNECTIONS)
        self.timeout = timeout
        self.create_client = create_client
        self.server_socket = None
        self.server_fileno = None
        if server_socket is None:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind((address, port))
                server_socket.listen(5)
            except:
                raise
        else:
            if server_socket == 0:
                server_socket = None
            else:
                server_socket = socket.fromfd(server_socket, socket.AF_INET,
                                              socket.SOCK_STREAM)
        if server_socket:
            self.server_socket = server_socket
            self.server_fileno = server_socket.fileno()
        # Dictionary of active clients,
        # key = file descriptor, value = TelnetClient instance
        self.clients = {}

    def stop(self):
        """Disconnect all clients and shut down the server."""
        for clients in self.client_list():
            clients.sock.close()
        if self.server_socket:
            self.server_socket.close()

    def client_count(self):
        """Return the number of active connections.

        :returns int: The client count

        """
        return len(self.clients)

    def client_list(self):
        """Return a list of connected clients.

        :returns iterable: The client list

        """
        return self.clients.values()

    def poll(self):

        """Poll clients for states changes and send/receive data.

        This performs a non-blocking scan of recv and send states on the server
        and client connection sockets, then processes new connection requests,
        reads incoming data, and sends outgoing data. Sends and receives may
        be partial.

        """

        # Build a list of connections to test for receive data pending.
        recv_list = []
        if self.server_socket:
            recv_list.append(self.server_fileno)

        del_list = []  # List of clients to delete after polling.

        for client in self.clients.values():
            if client.active:
                recv_list.append(client.fileno)
            else:
                if self.on_disconnect:
                    self.on_disconnect(client)
                del_list.append(client.fileno)

        # Delete inactive connections from the dictionary.
        for client in del_list:
            del self.clients[client]

        # Build a list of connections that need to send data.
        send_list = []
        for client in self.clients.values():
            if client.send_buffer:
                send_list.append(client.fileno)

        # Don't poll with three empty lists, Windows won't like it.
        # (And it's a waste of time?)
        if not recv_list and not send_list:
            return

        # Get active socket file descriptors from select.select().
        try:
            rlist, slist, elist = select.select(recv_list, send_list, [],
                                                self.timeout)
        except select.error as err:
            # If we can't even use select(), game over man, game over..
            logging.critical("SELECT socket error '{}'".format(str(err)))
            raise

        # Process socket file descriptors with data to receive.
        for sock_fileno in rlist:

            # If it's coming from the server's socket then
            # this is a new connection request.
            if self.server_socket and sock_fileno == self.server_fileno:

                try:
                    sock, addr_tup = self.server_socket.accept()
                except socket.error as err:
                    # noinspection PyUnresolvedReferences
                    logging.error("ACCEPT socket error '{}:{}'."
                                  .format(err[0], err[1]))
                    continue

                # Check for maximum connections.
                if self.client_count() >= self.max_connections:
                    logging.warning("Refusing new connection, "
                                    "maximum already in use.")
                    sock.close()
                    continue

                if self.create_client:
                    # Create the client instance.
                    new_client = TelnetClient(sock, addr_tup)
                    # Add the connection to our dictionary and call handler.
                    self.clients[new_client.fileno] = new_client
                    if self.on_connect:
                        self.on_connect(new_client)
                elif self.on_connect:
                    self.on_connect(sock, addr_tup)

            else:
                # Call the connection's receive method.
                try:
                    self.clients[sock_fileno].socket_recv()
                except ConnectionLost:
                    self.clients[sock_fileno].deactivate()
                    # Don't wait another poll to do this.. -WH
                    if self.on_disconnect:
                        self.on_disconnect(self.clients[sock_fileno])
                    del self.clients[sock_fileno]
                    if sock_fileno in slist:
                        slist.remove(sock_fileno)

        # Process sockets with data to send.
        for sock_fileno in slist:
            # Call the connection's send method.
            self.clients[sock_fileno].socket_send()
