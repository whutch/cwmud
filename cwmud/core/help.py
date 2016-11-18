# -*- coding: utf-8 -*-
"""Help information management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import fnmatch
import re

from .utils.bases import Manager


class HelpSourceManager(Manager):

    """A manager for help source registration."""

    def find(self, pattern):
        """Find one or more help entries matching a pattern.

        :param str pattern: A pattern to match entries against
        :returns list: A list of HelpEntry instances that match the pattern

        """
        found = {}
        for source in self._items.values():
            for entry in source.find(pattern):
                if entry.key not in found:
                    found[entry.key] = entry
        return list(found.values())


class HelpSource:

    """A searchable source of help data."""

    def __init__(self):
        """Create a new help source."""
        self._entries = {}

    def __contains__(self, key):
        return key in self._entries

    def __getitem__(self, key):
        return self._entries[key]

    def __setitem__(self, key, value):
        self._entries[key] = value

    def __delitem__(self, key):
        del self._entries[key]

    def __iter__(self):
        return iter(self._entries)

    def keys(self):
        """Return an iterator through this source's entry keys."""
        return self._entries.keys()

    def entries(self):
        """Return an iterator through this source's entries."""
        return self._entries.values()

    def find(self, pattern):
        """Find one or more help entries matching a pattern.

        :param str pattern: A pattern to match entries against
        :returns list: A list of HelpEntry instances that match the pattern

        """
        pattern = re.compile(fnmatch.translate(pattern))
        matches = []
        for entry in self.entries():
            for topic in entry.topics:
                if pattern.match(topic):
                    matches.append(entry)
        return matches


class HelpEntry:

    """A single entry of help information."""

    def __init__(self, key, title, text):
        """Create a new help entry."""
        self._key = key
        self._related = set()
        self._text = text
        self._title = title
        self._topics = set()

    @property
    def related(self):
        """Return this entry's related topics."""
        return frozenset(self._related)

    @property
    def text(self):
        """Return this entry's text."""
        return self._text

    @property
    def topics(self):
        """Return this entry's topic keywords."""
        return frozenset(self._topics)


HELP_SOURCES = HelpSourceManager()
