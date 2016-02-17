# -*- coding: utf-8 -*-
"""Tests for logging."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from datetime import datetime
import logging
import uuid

from cwmud import settings
from cwmud.core.logs import _Formatter, get_logger


class TestLogs:

    """A collection of tests for logging."""

    log = None

    def test_logger_create(self):
        """Test that our get_logger function returns a Logger instance."""
        type(self).log = get_logger("tests")
        assert isinstance(self.log, logging.Logger)

    def test_logger_write(self):
        """Test that a Logger writes to our log file."""
        test_uuid = str(uuid.uuid1())
        self.log.debug("Log test - %s", test_uuid)
        with open(settings.LOG_PATH) as log_file:
            last_line = log_file.readlines()[-1]
            assert last_line.rstrip().endswith(test_uuid)


class TestFormatter:

    """A collection of tests for our log formatter."""

    record = None
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
        cls.record = logging.LogRecord(None, None, "", 0, "", (), None, None)
        cls.record.created = 1412096845.010138
        cls.record.msecs = 10.13803482055664

    def test_format_time_default(self):
        """Test calling formatTime without a datefmt argument.

        Doing so will cause it to fall back to the formatTime method on
        the logging library's Formatter class.

        """
        line = self.formatter.formatTime(self.record)
        formatter = logging.Formatter()
        assert line == formatter.formatTime(self.record)

    def test_format_time_console(self):
        """Test calling formatTime with the console logging format."""
        line = self.formatter.formatTime(self.record, self.console_format)
        dt = datetime.fromtimestamp(self.record.created)
        assert line == dt.strftime(self.console_format[:-3]) + ",010"

    def test_format_time_file(self):
        """Test calling formatTime with the file logging format."""
        line = self.formatter.formatTime(self.record, self.file_format)
        dt = datetime.fromtimestamp(self.record.created)
        assert line == dt.strftime(self.file_format[:-3]) + ",010"
