# -*- coding: utf-8 -*-
"""Logging configuration and support."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from datetime import datetime
import logging
from logging.config import dictConfig
from os import makedirs
from os.path import dirname, exists
import re

from .. import settings


# Make sure the folder where our log will go exists.
if not exists(dirname(settings.LOG_PATH)):
    # We can't test this without reload the module and doing so breaks
    # a bunch of other tests that rely on logging.
    makedirs(dirname(settings.LOG_PATH))  # pragma: no cover


class _Formatter(logging.Formatter):

    """Custom formatter for our logging handlers."""

    def formatTime(self, record, datefmt=None):
        """Convert a LogRecord's creation time to a string.

        If `datefmt` is provided, it will be used to convert the time through
        datetime.strftime.  If not, it falls back to the formatTime method of
        logging.Formatter, which converts the time through time.strftime.

        This custom processing allows for the full range of formatting options
        provided by datetime.strftime as opposed to time.strftime.

        There is additional parsing done to allow for the %F argument to be
        converted to 3-digit zero-padded milliseconds, as an alternative to
        the %f argument's usual 6-digit microseconds (because frankly that's
        just too many digits).

        :param LogRecord record: The record to be formatted
        :param str datefmt: A formatting string to be passed to strftime
        :returns str: A formatted time string

        """
        if datefmt:
            msecs = str(int(record.msecs)).zfill(3)
            datefmt = re.sub(r"(?<!%)%F", msecs, datefmt)
            parsed_time = datetime.fromtimestamp(record.created)
            return parsed_time.strftime(datefmt)
        else:
            return super().formatTime(record)


# Load our log configuration into Python's logging module.
dictConfig({
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "file": {
            "()": _Formatter,
            "format": "%(asctime)s  %(name)-12s  %(levelname)-8s %(message)s",
            "datefmt": settings.LOG_TIME_FORMAT_FILE,
        },
        "console": {
            "()": _Formatter,
            "format": "%(asctime)s  %(name)-10s  %(levelname)-8s %(message)s",
            "datefmt": settings.LOG_TIME_FORMAT_CONSOLE,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "console",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "DEBUG",
            "formatter": "file",
            "filename": settings.LOG_PATH,
            "when": settings.LOG_ROTATE_WHEN,
            "interval": settings.LOG_ROTATE_INTERVAL,
            "utc": settings.LOG_UTC_TIMES,
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
})


def get_logger(*args, **kwargs):
    """Fetch an instance of logging.Logger.

    This is just a stub that can later be expanded if we want to perform any
    processing on the Logger instance before passing it on.

    Using this as a middle-man also ensures that our logging configuration will
    always be loaded before a Logger is used, as none of the other code will
    load the logging module directly.

    :param sequence args: Positional arguments passed on to logging.getLogger
    :param mapping kwargs: Keyword arguments passed on to logging.getLogger
    :returns logging.Logger: A Logger instance

    """
    logger = logging.getLogger(*args, **kwargs)
    return logger
