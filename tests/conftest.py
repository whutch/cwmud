# -*- coding: utf-8 -*-
"""Configuration for testing through py.test."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os.path import abspath, dirname, join
import sys
import time

import redis

# Until Atria is an installable package, we need to add it to our Python path
# so that we can do "from atria" imports in the tests.
TEST_ROOT = dirname(abspath(__file__))
sys.path.insert(0, dirname(TEST_ROOT))

from atria import ROOT_DIR, settings


# Change the log path during testing.
settings.LOG_PATH = join(ROOT_DIR, "logs", "test.log")

settings.BIND_ADDRESS = "localhost"
# Use a different listen port, in case the tests are run while a
# real server is running on the same system.
settings.BIND_PORT = 4445


from atria.core.logs import get_logger

log = get_logger("tests")


# Send out a message to signal the starts of a test run.
rdb = redis.StrictRedis(decode_responses=True)
rdb.publish("tests-start", time.time())
log.debug("====== TESTS START ======")
