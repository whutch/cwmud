# -*- coding: utf-8 -*-
"""Pickle serialization and storage."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os import listdir, makedirs, remove
from os.path import abspath, exists, join, splitext
import pickle

from .. import settings
from .storage import DataStore
from .utils.funcs import joins


class PickleStore(DataStore):

    """A store that pickles its data."""

    _opens = False

    def __init__(self, subpath):
        """Create a new pickle store."""
        super().__init__()
        self._path = join(settings.DATA_DIR, "pickle", subpath)
        # Make sure the path to the pickle store exists.
        if not exists(self._path):
            makedirs(self._path)

    def _get_key_path(self, key):
        """Validate and return an absolute path for a pickle file.

        :param str key: The key to store the data under
        :returns str: An absolute path to the pickle file for that key
        :raises OSError: If the path is not under this store's base path
        :raises TypeError: If the key is not a string

        """
        if not isinstance(key, str):
            raise TypeError("pickle keys must be strings")
        path = abspath(join(self._path, key + ".pkl"))
        if not path.startswith(abspath(self._path)):
            raise OSError(joins("invalid path to pickle file:", path))
        return path

    def _is_open(self):  # pragma: no cover
        return True

    def _open(self):  # pragma: no cover
        pass

    def _close(self):  # pragma: no cover
        pass

    def _keys(self):
        """Return an iterator through the pickle files in this store."""
        for name in listdir(abspath(self._path)):
            key, ext = splitext(name)
            if ext == ".pkl":
                yield key

    def _has(self, key):
        """Return whether a pickle file exists or not."""
        path = self._get_key_path(key)
        return exists(path)

    def _get(self, key):
        """Fetch the data from a pickle file."""
        path = self._get_key_path(key)
        with open(path, "rb") as pickle_file:
            return pickle.load(pickle_file)

    def _put(self, key, data):
        """Store data in a pickle file."""
        path = self._get_key_path(key)
        with open(path, "wb") as pickle_file:
            pickle.dump(data, pickle_file)

    def _delete(self, key):
        """Delete a pickle file."""
        path = self._get_key_path(key)
        remove(path)
