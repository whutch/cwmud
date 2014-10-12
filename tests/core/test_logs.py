# -*- coding: utf-8 -*-
"""Tests for logging."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import logging
import uuid

from atria import settings
from atria.core.logs import _Formatter, get_logger


class XTestFormatter:

    """A collection of tests for our log formatter."""

    record = logging.LogRecord(None, None, "", 0, "", (), None, None)
    formatter = _Formatter()
    # The console and file formats are hard-coded here instead of pulled
    # from settings, so this doesn't test errors in your custom formats
    # if they differ, it only tests that the formatTime method of our
    # formatter class is working.
    console_format = "%H:%M:%S,%F"
    file_format = "%Y-%m-%d %a %H:%M:%S,%F"

    @classmethod
    def setup_class(cls):
        """Set up these formatter tests with a hard-coded time."""
        cls.record.created = 1412096845.010138
        cls.record.msecs = 10.13803482055664

    def test_format_time_default(self):
        """Test calling formatTime without a datefmt argument.

        Doing so will cause it to fall back to the formatTime method on
        the logging library's Formatter class.

        """
        line = self.formatter.formatTime(self.record)
        assert line == "2014-09-30 12:07:25,010"

    def test_format_time_console(self):
        """Test calling formatTime with the console logging format."""
        line = self.formatter.formatTime(self.record, self.console_format)
        assert line == "12:07:25,010"

    def test_format_time_file(self):
        """Test calling formatTime with the file logging format."""
        line = self.formatter.formatTime(self.record, self.file_format)
        assert line == "2014-09-30 Tue 12:07:25,010"


def test_create_logger():
    """Test that our get_logger function returns a Logger."""
    log = get_logger("tests")
    assert isinstance(log, logging.Logger)


def test_log_write():
    """Test that a Logger writes to our log file."""
    log = get_logger("tests")
    test_uuid = str(uuid.uuid1())
    log.debug("Log test - %s", test_uuid)
    with open(settings.LOG_PATH) as log_file:
        last_line = log_file.readlines()[-1]
        assert last_line.rstrip().endswith(test_uuid)
