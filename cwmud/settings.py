# -*- coding: utf-8 -*-
"""Core settings and configuration."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os.path import join

from . import ROOT_DIR


DEBUG = True

# General
MUD_NAME = "Clockwork"
MUD_NAME_FULL = "Clockwork MUD Server"

# Networking
BIND_ADDRESS = "127.0.0.1"
BIND_PORT = 4000
IDLE_TIME = 180  # seconds
IDLE_TIME_MAX = 600  # seconds

# Logging
LOG_PATH = join(ROOT_DIR, "logs", "mud.log")
LOG_TIME_FORMAT_CONSOLE = "%H:%M:%S,%F"
LOG_TIME_FORMAT_FILE = "%Y-%m-%d %a %H:%M:%S,%F"
LOG_ROTATE_WHEN = "midnight"
LOG_ROTATE_INTERVAL = 1
LOG_UTC_TIMES = False

# Storage
DATA_DIR = join(ROOT_DIR, "data")

# Optional modules
INCLUDE_MODULES = [
    # These should be import paths relative to the base package.
    # ".contrib.my_module",
]

# Advanced
FORCE_GC_COLLECT = False
