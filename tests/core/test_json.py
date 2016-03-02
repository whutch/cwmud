# -*- coding: utf-8 -*-
"""Tests for JSON data storage."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os.path import exists, join
from shutil import rmtree

import pytest

from cwmud import settings
from cwmud.core.json import JSONStore


class TestJSONStores:

    """A collection of tests for JSON stores."""

    store = None
    store_path = join(settings.DATA_DIR, "json", "test")
    json_path = join(store_path, "test.json")
    data = {"test": 123, "yeah": "okay"}

    @classmethod
    def setup_class(cls):
        """Clean up any previous test data directory."""
        # In case tests were previously interrupted.
        if exists(cls.store_path):
            rmtree(cls.store_path)

    @classmethod
    def teardown_class(cls):
        """Clean up our test data directory."""
        if exists(cls.store_path):
            rmtree(cls.store_path)

    def test_jsonstore_create(self):
        """Test that we can create a new JSON data store."""
        # The path to this store's data shouldn't exist yet.
        assert not exists(self.store_path)
        type(self).store = JSONStore("test")
        # The directory for this store's data should have been created.
        assert exists(self.store_path)
        assert self.store

    def test_jsonstore_create_second(self):
        """Test that we can create a second JSON store with the same path."""
        assert JSONStore("test")

    def test_jsonstore_get_key_path(self):
        """Test that we can get the full path of a JSON file by key."""
        assert self.store._get_key_path("test") == self.json_path

    def test_jsonstore_get_key_path_key_not_string(self):
        """Test that trying to use a non-string as a JSON key fails."""
        with pytest.raises(TypeError):
            self.store._get_key_path(5)
        with pytest.raises(TypeError):
            self.store._get_key_path(False)

    def test_jsonstore_get_key_path_invalid_path(self):
        """Test that trying to get a key path outside a store fails."""
        with pytest.raises(OSError):
            self.store._get_key_path("../../test")

    def test_jsonstore_no_keys(self):
        """Test that we can check if a JSON store has no keys."""
        assert not tuple(self.store.keys())

    def test_jsonstore_put(self):
        """Test that we can put data into a JSON store."""
        assert not exists(self.json_path)
        self.store._put("test", self.data)
        assert exists(self.json_path)

    def test_jsonstore_has(self):
        """Test that we can tell if a JSON store has a key."""
        assert self.store._has("test")
        assert not self.store._has("nonexistent_key")

    def test_jsonstore_keys(self):
        """Test that we can iterate through a JSON store's keys."""
        # We need to stick a non-JSON file in there to ensure it isn't
        # picked up as a key.
        with open(join(self.store_path, "nope.pkl"), "w") as out:
            out.write("\n")
        # And let's put another valid key in for good measure.
        self.store._put("yeah", {})
        assert tuple(sorted(self.store._keys())) == ("test", "yeah")

    def test_jsonstore_get(self):
        """Test that we can get data from a JSON store."""
        assert self.store._get("test") == self.data

    def test_jsonstore_delete(self):
        """Test that we can delete data from a JSON store."""
        assert exists(self.json_path)
        assert self.store._has("test")
        self.store._delete("test")
        assert not exists(self.json_path)
        assert not self.store._has("test")
