# -*- coding: utf-8 -*-
"""Data collections and attributes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import abc

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins
from .utils.mixins import HasWeaks, HasWeaksMeta


log = get_logger("attrs")


# noinspection PyDocstring
class _DataBlobMeta(HasWeaksMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._blobs = {}
        cls._attrs = {}

    def register_blob(cls, name):

        """Decorate a data blob to register it in this blob.

        :param str name: The name of the field to store the blob
        :returns None:
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
        :returns None:
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


class DataBlob(HasWeaks, metaclass=_DataBlobMeta):

    """A collection of attributes and sub-blobs on an entity."""

    # These are overridden in the metaclass, I just put them here
    # to avoid a lot of unresolved reference errors in IDE introspection.
    _blobs = None
    _attrs = None

    def __init__(self, entity):
        super().__init__()
        self._entity = entity
        self._attr_values = {}
        for key, attr in self._attrs.items():
            # noinspection PyProtectedMember
            self._attr_values[key] = attr.get_default(entity)
        self._blobs = self._blobs.copy()
        for key, blob in self._blobs.items():
            self._blobs[key] = blob(entity)

    @property
    def _entity(self):
        return self._get_weak("entity")

    @_entity.setter
    def _entity(self, new_entity):
        self._set_weak("entity", new_entity)

    def _get_attr_val(self, name):
        return self._attr_values.get(name)

    # noinspection PyProtectedMember
    def _set_attr_val(self, name, value, validate=True, raw=False):
        attr = self._attrs[name]
        old_value = self._attr_values.get(name)
        entity = self._entity
        if value is not Unset:
            if validate:
                value = attr.validate(entity, value)
            if not raw:
                value = attr.finalize(entity, value)
        self._attr_values[name] = value
        entity.dirty()
        attr.changed(entity, self, old_value, value)
        # Update entity caches.
        cache = entity._caches.get(name)
        if cache:
            if old_value in cache:
                cache[old_value].discard(entity)
            if value not in cache:
                cache[value] = {entity}
            else:
                cache[value].add(entity)

    def _update(self, blob):
        """Merge this blob with another, replacing blobs and attrs.

        Sub-blobs and attrs on the given blob with take precedent over those
        existing on this blob.

        :param DataBlob blob: The blob to merge this blob with
        :returns None:

        """
        self._blobs.update(blob._blobs)
        self._attrs.update(blob._attrs)
        self._attr_values.update(blob._attr_values)

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
            if value is Unset:
                value = "unset"
            else:
                # noinspection PyProtectedMember
                value = attr.serialize(self._entity, value)
            data[key] = value
        return data

    def deserialize(self, data):
        """Update this blob's data using values from a dict.

        All sub-blobs found will in turn be deserialized.  Be careful where
        you deserialize data from, as it will be loaded raw and unvalidated.

        :param dict data: The data to deserialize
        :returns None:

        """
        for key, value in data.items():
            if key in self._attrs:
                if value == "unset":
                    value = Unset
                else:
                    # noinspection PyProtectedMember
                    value = self._attrs[key].deserialize(self._entity, value)
                self._set_attr_val(key, value, validate=False, raw=True)
            elif key in self._blobs:
                self._blobs[key].deserialize(value)
            else:
                log.warning(joins("Unused data while deserializing ",
                                  class_name(self), ": '", key, "':'",
                                  value, "'.", sep=""))


class _UnsetMeta(type):

    def __repr__(cls):
        return "<Unset>"

    def __bool__(cls):
        return False


class Unset(metaclass=_UnsetMeta):

    """A unique value to note that an attribute hasn't been set."""


class Attribute:

    """A single attribute of an entity.

    These are templates for the behavior of an attribute, they will not be
    instantiated and as such have no instance-based variables.

    The value of `default` should not be set to a mutable type, as it will
    be passed by reference to all instantiated blobs and risks being changed
    elsewhere in the code.

    """

    _default = Unset  # Do NOT use mutable types for this.
    _read_only = False

    @classmethod
    def get_default(cls, entity):
        """Get the default value for this attribute.

        :param entity: The entity this attribute is on
        :returns: The default value

        """
        return cls._default

    @classmethod
    def validate(cls, entity, new_value):
        """Validate a value for this attribute.

        This will be called by the blob when setting the value for this
        attribute, override it to perform any checks or sanitation.  This
        should either return a valid value for the attribute or raise an
        exception as to why the value is invalid.

        :param entity: The entity this attribute is on
        :param new_value: The potential value to validate
        :returns: The validated (and optionally sanitized) value

        """
        return new_value

    @classmethod
    def finalize(cls, entity, new_value):
        """Finalize the value for this attribute.

        This will be called by the blob when setting the value for this
        attribute, after validation; override it to perform any sanitation
        or transformation. The value should be considered valid.

        :param entity: The entity this attribute is on
        :param new_value: The new, validated value
        :returns: The finalized value
        """
        return new_value

    @classmethod
    def changed(cls, entity, blob, old_value, new_value):
        """Perform any actions necessary after this attribute's value changes.

        This will be called by the blob after the value of this attribute
        has changed, override it to do any necessary post-setter actions.

        :param entity: The entity this attribute is on
        :param DataBlob blob: The blob that changed
        :param old_value: The previous value
        :param new_value: The new value
        :returns None:

        """

    @classmethod
    def serialize(cls, entity, value):
        """Serialize a value for this attribute that is suitable for storage.

        This will be called by the blob when serializing itself, override it
        to perform any necessary conversion or sanitation.

        :param entity: The entity this attribute is on
        :param value: The value to serialize
        :returns: The serialized value

        """
        return value

    @classmethod
    def deserialize(cls, entity, value):
        """Deserialize a value for this attribute from storage.

        This will be called by the blob when deserializing itself, override it
        to perform any necessary conversion or sanitation.

        :param entity: The entity this attribute is on
        :param value: The value to deserialize
        :returns: The deserialized value

        """
        return value


class MutableAttribute(Attribute):

    """A mutable attribute of an entity."""

    _read_only = True

    class Proxy:

        def __init__(self, entity):
            raise NotImplementedError

    @classmethod
    def get_default(cls, entity):
        """Return a bound proxy instance for this mutable attribute.

        :param entity: The entity this attribute is on
        :returns: A bound proxy instance

        """
        return cls.Proxy(entity)


class ListAttribute(MutableAttribute):

    """An entity attribute that proxies a list."""

    class Proxy(abc.MutableSequence):

        def __init__(self, entity, items=()):
            self._items = list(items)
            self._entity = entity

        def __getitem__(self, index):
            return self._items[index]

        def __setitem__(self, index, value):
            self._items[index] = value
            self._entity.dirty()

        def __delitem__(self, index):
            del self._items[index]
            self._entity.dirty()

        def __len__(self):
            return len(self._items)

        def insert(self, index, value):
            self._items.insert(index, value)
            self._entity.dirty()


class DictAttribute(MutableAttribute):

    """An entity attribute that proxies a dictionary."""

    class Proxy(abc.MutableMapping):

        def __init__(self, entity, items=None):
            self._items = dict(items or {})
            self._entity = entity

        def __getitem__(self, key):
            return self._items[key]

        def __setitem__(self, key, value):
            self._items[key] = value
            self._entity.dirty()

        def __delitem__(self, key):
            del self._items[key]
            self._entity.dirty()

        def __len__(self):
            return len(self._items)

        def __iter__(self):
            return iter(self._items)


class SetAttribute(MutableAttribute):

    """An entity attribute that proxies a set."""

    class Proxy(abc.MutableSet):

        def __init__(self, entity, items=()):
            self._items = set(items)
            self._entity = entity

        def __len__(self):
            return len(self._items)

        def __iter__(self):
            return iter(self._items)

        def __contains__(self, value):
            return value in self._items

        def add(self, value):
            self._items.add(value)
            self._entity.dirty()

        def discard(self, value):
            self._items.discard(value)
            self._entity.dirty()
