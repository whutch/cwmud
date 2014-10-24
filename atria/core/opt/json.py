# -*- coding: utf-8 -*-
"""JSON data storage."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os import makedirs, remove
from os.path import abspath, exists, join
import json

from ... import settings
from ..storage import DataStore
from ..utils.funcs import joins


class JSONStore(DataStore):

    """A store that keeps its data in the JSON format."""

    _opens = False

    def __init__(self, subpath, indent=None, separators=None):
        """Create a new JSON store."""
        super().__init__()
        self._path = join(settings.DATA_DIR, "json", subpath)
        self._indent = indent
        self._separators = separators
        # Make sure the path to the JSON store exists
        if not exists(self._path):
            makedirs(self._path)

    def _get_key_path(self, key):
        """Validate and return an absolute path for a JSON file.

        :param str key: The key to store the data under
        :returns str: An absolute path to the JSON file for that key
        :raises OSError: If the path is not under this store's base path
        :raises TypeError: If the key is not a string

        """
        if not isinstance(key, str):
            raise TypeError("JSON keys must be strings")
        path = abspath(join(self._path, key + ".json"))
        if not path.startswith(abspath(self._path)):
            raise OSError(joins("invalid path to JSON file:", path))
        return path

    def _has(self, key):
        """Return whether a JSON file exists or not."""
        path = self._get_key_path(key)
        return exists(path)

    def _get(self, key):
        """Fetch the data from a JSON file."""
        path = self._get_key_path(key)
        with open(path, "r") as json_file:
            return json.load(json_file)

    def _put(self, key, data):
        """Store data in a JSON file."""
        path = self._get_key_path(key)
        with open(path, "w") as json_file:
            json.dump(data, json_file, indent=self._indent,
                      separators=self._separators)

    def _delete(self, key):
        """Delete a JSON file."""
        path = self._get_key_path(key)
        remove(path)
