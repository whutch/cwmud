# -*- coding: utf-8 -*-
"""Entities, the base of all complex MUD objects."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins


log = get_logger("entities")


# noinspection PyDocstring
class _DataBlobMeta(type):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._blobs = {}
        cls._attrs = {}

    def register_blob(cls, name):

        """Decorate a data blob to register it in this blob.

        :param str name: The name of the field to store the blob
        :returns: None
        :raises AlreadyExists: If the given name already exists as an attr
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of DataBlob

        """
        if hasattr(cls, name):
            raise AlreadyExists(name, getattr(cls, name))

        # noinspection PyProtectedMember
        def _inner(blob_class):
            if (not isinstance(blob_class, type) or
                    not issubclass(blob_class, DataBlob)):
                raise TypeError("must be subclass of DataBlob to register")
            cls._blobs[name] = blob_class
            setattr(cls, name, property(lambda s: s._blobs[name]))
            return blob_class

        return _inner

    def register_attr(cls, name):

        """Decorate an attribute to register it in this blob.

        :param str name: The name of the field to store the attribute
        :returns: None
        :raises AlreadyExists: If the given name already exists as an attr
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Attribute

        """
        if hasattr(cls, name):
            raise AlreadyExists(name, getattr(cls, name))

        # noinspection PyProtectedMember
        def _inner(attr_class):
            if (not isinstance(attr_class, type) or
                    not issubclass(attr_class, Attribute)):
                raise TypeError("must be subclass of Attribute to register")
            cls._attrs[name] = attr_class
            getter = lambda s: s._get_attr_val(name)
            setter = (lambda s, v: s._set_attr_val(name, v)
                      if not attr_class._read_only else None)
            setattr(cls, name, property(getter, setter))
            return attr_class

        return _inner


class DataBlob(metaclass=_DataBlobMeta):

    """A collection of attributes and sub-blobs on an entity."""

    # These are overridden in the metaclass, I just put them here
    #  to avoid a lot of unresolved reference errors in IDE introspection
    _blobs = {}
    _attrs = {}

    def __init__(self):
        self._attr_values = {}
        for key, attr in self._attrs.items():
            # noinspection PyProtectedMember
            self._attr_values[key] = attr._default
        self._blobs = self._blobs.copy()
        for key, blob in self._blobs.items():
            self._blobs[key] = blob()

    def _get_attr_val(self, name):
        return self._attr_values.get(name)

    def _set_attr_val(self, name, value):
        attr = self._attrs[name]
        # noinspection PyProtectedMember
        self._attr_values[name] = attr._validate(value)

    def serialize(self):
        """Create a dict from this blob, sanitized and suitable for storage.

        All sub-blobs will in turn be serialized.

        :returns dict: The serialized data

        """
        data = {}
        for key, blob in self._blobs.items():
            data[key] = blob.serialize()
        for key, attr in self._attrs.items():
            if key in data:
                raise KeyError(joins("duplicate blob key:", key))
            value = self._attr_values.get(key)
            # noinspection PyProtectedMember
            data[key] = attr._serialize(value)
        return data

    def deserialize(self, data):
        """Update this blob's data using values from a dict.

        All sub-blobs found will in turn be deserialized.

        :param dict data: The data to deserialize
        :returns: None

        """
        for key, value in data.items():
            if key in self._attrs:
                # noinspection PyProtectedMember
                value = self._attrs[key]._deserialize(value)
                self._set_attr_val(key, value)
            elif key in self._blobs:
                self._blobs[key].deserialize(value)
            else:
                log.warn(joins("Unused data while deserializing ",
                               class_name(self), ": '", key, "':'",
                               value, "'", sep=""))


class Attribute:

    """A single attribute of an entity.

    These are templates for the behavior of an attribute, they will not be
    instantiated and as such have no instance-based variables.

    The value of `_default` should not be set to a mutable type, as it will
    be passed by reference to all instantiated blobs and risks being changed
    elsewhere in the code.

    """

    _default = None  # Do NOT use mutable types for this
    _read_only = False

    @classmethod
    def _validate(cls, new_value):
        """Validate a value for this attribute.

        This will be called by the blob when setting the value for this
        attribute, override it to perform any checks or sanitation. This
        should either return a valid value for the attribute or raise an
        exception as to why the value is invalid.

        :param new_value: The potential value to validate
        :returns: The validated (and optionally sanitized) value

        """
        return new_value

    @classmethod
    def _serialize(cls, value):
        """Serialize a value for this attribute that is suitable for storage.

        This will be called by the blob when serializing itself, override it
        to perform any necessary conversion or sanitation.

        :param value: The value to serialize
        :returns: The serialized value

        """
        return value

    @classmethod
    def _deserialize(cls, value):
        """Deserialize a value for this attribute from storage.

        This will be called by the blob when deserializing itself, override it
        to perform any necessary conversion or sanitation.

        :param value: The value to deserialize
        :returns: The deserialized value

        """
        return value
