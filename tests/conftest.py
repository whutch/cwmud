# -*- coding: utf-8 -*-
"""Configuration for testing through py.test."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os.path import abspath, dirname, join
import sys

# Until Atria is an installable package, we need to add it to our Python path
#  so that we can do "from atria" imports in the tests.
TEST_ROOT = dirname(abspath(__file__))
sys.path.insert(0, dirname(TEST_ROOT))


from atria import ROOT_DIR, settings

# Change the log path during testing
settings.LOG_PATH = join(ROOT_DIR, "logs", "test.log")
