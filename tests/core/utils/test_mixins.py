# -*- coding: utf-8 -*-
"""Tests for mix-in support classes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import gc
from weakref import finalize

from cwmud.core.utils.mixins import HasFlags, HasParent, HasTags, HasWeaks


class TestHasFlags:

    """A collection of tests for the flagging mix-in class."""

    class _TestClass(HasFlags):

        def __init__(self):
            super().__init__()
            self.changed = 0

        def _flags_changed(self):
            self.changed += 1

    instance = _TestClass()

    def test_flags_property(self):
        """Test that the flags property returns a flag set."""
        assert hasattr(self.instance.flags, "toggle")

    def test_contains_flag(self):
        """Test that we can check if the set contains a flag."""
        assert "test" not in self.instance.flags

    def test_add_flag(self):
        """Test that we can add one flag to the flag set."""
        self.instance.flags.add("test")
        assert "test" in self.instance.flags

    def test_add_multiple_flags(self):
        """Test that we can add multiple flags at once."""
        self.instance.flags.add(1, 2)
        assert 1 in self.instance.flags and 2 in self.instance.flags

    def test_changed_callback(self):
        """Test that modifying the flag set triggers a callback."""
        had_changed = self.instance.changed
        self.instance.flags.toggle(3)
        assert self.instance.changed == had_changed + 1
        self.instance.flags.toggle(3)
        assert self.instance.changed == had_changed + 2
        # Ensure that nothing breaks if there is no owner.
        owner_ref = self.instance.flags._owner_ref
        self.instance.flags._owner_ref = None
        self.instance.flags.toggle(3)
        assert self.instance.changed == had_changed + 2
        self.instance.flags._owner_ref = owner_ref
        self.instance.flags.toggle(3)
        assert self.instance.changed == had_changed + 3

    def test_flags_as_tuple(self):
        """Test that we cam get the current flags as a tuple."""
        assert set(self.instance.flags.as_tuple) == {"test", 1, 2}

    def test_iter_flags(self):
        """Test that we can iterate through the flag set."""
        assert {flag for flag in self.instance.flags} == {"test", 1, 2}

    def test_drop_flag(self):
        """Test that we can drop one flag from the flag set."""
        assert "test" in self.instance.flags
        self.instance.flags.drop("test")
        assert "test" not in self.instance.flags

    def test_drop_multiple_flags(self):
        """Test that we can drop multiple flags at once."""
        assert (1 in self.instance.flags and
                2 in self.instance.flags and
                3 not in self.instance.flags)
        self.instance.flags.drop(1, 2, 3)
        assert (1 not in self.instance.flags and
                2 not in self.instance.flags and
                3 not in self.instance.flags)

    def test_toggle_flags(self):
        """Test that we can toggle one flag in the flag set."""
        assert "test" not in self.instance.flags
        self.instance.flags.toggle("test")
        assert "test" in self.instance.flags

    def test_toggle_multiple_flags(self):
        """Test that we can toggle multiple flags at once."""
        assert "test" in self.instance.flags
        assert 1 not in self.instance.flags and 2 not in self.instance.flags
        self.instance.flags.toggle("test", 1, 2)
        assert "test" not in self.instance.flags
        assert 1 in self.instance.flags and 2 in self.instance.flags

    def test_flags_as_bool(self):
        """Test that we can use the flag set in a boolean statement."""
        assert self.instance.flags
        self.instance.flags.toggle(1, 2)
        assert not self.instance.flags

    def test_has_flag(self):
        """Test that we can check for a flag through the has method."""
        assert not self.instance.flags.has("test")
        self.instance.flags.toggle("test")
        assert self.instance.flags.has("test")
        # Ensure that the class itself has a separate flag set.
        assert not self._TestClass.flags

    def test_has_multiple_flags(self):
        """Test that we can check for multiple flags through the has method."""
        assert not self.instance.flags.has("test", 1, 2)
        self.instance.flags.toggle(1, 2)
        assert self.instance.flags.has("test", 1, 2)

    def test_has_any_flags(self):
        """Test that we can check for flags through the has_any method."""
        assert not self.instance.flags.has_any("nope", 3, 4)
        assert self.instance.flags.has_any("test", 3, 4)

    def test_no_owner(self):
        """Test adding, dropping, and toggling with no owner."""
        owner_ref = self.instance.flags._owner_ref
        self.instance.flags._owner_ref = None
        assert not self.instance.flags.has(5)
        self.instance.flags.add(5)
        assert self.instance.flags.has(5)
        self.instance.flags.drop(5)
        assert not self.instance.flags.has(5)
        self.instance.flags.toggle(5)
        assert self.instance.flags.has(5)
        self.instance.flags.toggle(5)
        assert not self.instance.flags.has(5)
        self.instance.flags._owner_ref = owner_ref


class TestHasTags:

    """A collection of tests for the tagging mix-in class."""

    class _TestClass(HasTags):

        def __init__(self):
            super().__init__()
            self.some_attribute = 5

    instance = _TestClass()

    def test_tags_property(self):
        """Test that the tags property returns a tag set."""
        assert hasattr(self.instance.tags, "as_dict")

    def test_contains_tag(self):
        """Test that we can check if the set contains a tag."""
        assert "test" not in self.instance.tags

    def test_set_tag(self):
        """Test that we can add a tag to the tag set."""
        self.instance.tags["test"] = 3
        assert "test" in self.instance.tags

    def test_get_tag(self):
        """Test that we can get a tag from the tag set."""
        assert self.instance.tags["test"] == 3

    def test_tags_as_dict(self):
        """Test that we can get the current tags as a dictionary."""
        assert self.instance.tags.as_dict == {"test": 3}

    def test_iter_tags(self):
        """Test that we can iterate through the tag set."""
        self.instance.tags["boop"] = True
        assert {tag for tag in self.instance.tags} == {"test", "boop"}

    def test_tags_length(self):
        """Test that we can get the number of tags."""
        assert len(self.instance.tags) == 2

    def test_remove_tag(self):
        """Test that we can remove a tag from the tag set."""
        assert "test" in self.instance.tags
        del self.instance.tags["test"]
        assert "test" not in self.instance.tags

    def test_tags_as_bool(self):
        """Test that we can use the tag set in a boolean statement."""
        assert self.instance.tags
        del self.instance.tags["boop"]
        assert not self.instance.tags

    def test_no_owner(self):
        """Test setting and removing tags with no owner."""
        owner_ref = self.instance.tags._owner_ref
        self.instance.tags._owner_ref = None
        assert "test" not in self.instance.tags
        self.instance.tags["test"] = 5
        assert "test" in self.instance.tags
        del self.instance.tags["test"]
        assert "test" not in self.instance.tags
        self.instance.tags._owner_ref = owner_ref


class TestHasWeaks:

    """A collection of tests for weak properties."""

    class _TestClass(HasWeaks):

        count = 0

        def __init__(self):
            super().__init__()
            type(self).count += 1
            finalize(self, type(self)._dec_count)

        @classmethod
        def _dec_count(cls):
            cls.count -= 1

        @property
        def weak_ref(self):
            """Get this object's weak reference."""
            return self._get_weak("weak_ref")

        @weak_ref.setter
        def weak_ref(self, obj):
            """Set this object's weak reference.

            :param any obj: The object we want to weakly reference
            :returns None:

            """
            self._set_weak("weak_ref", obj)

    def test_class_methods(self):
        """Test that we can get, set and delete weaks on classes."""
        instance = self._TestClass()
        assert not self._TestClass._get_weak("test")
        self._TestClass._set_weak("test", instance)
        assert self._TestClass._get_weak("test") is instance
        # Ensure that the weak reference was only added to the class and
        # not its instances.
        assert not instance._get_weak("test")
        self._TestClass._del_weak("test")
        assert not self._TestClass._get_weak("test")
        # Make sure deleting a non-existent weak reference doesn't explode.
        self._TestClass._del_weak("test")
        # Test that setting a weak to None removes it entirely.
        self._TestClass._set_weak("test", instance)
        assert self._TestClass._get_weak("test")
        self._TestClass._set_weak("test", None)
        # noinspection PyUnresolvedReferences
        assert "test" not in self._TestClass._weak_refs
        del instance
        gc.collect()

    def test_instance_methods(self):
        """Test that we can get, set and delete weaks on instances."""
        instance = self._TestClass()
        assert not instance._get_weak("test")
        instance._set_weak("test", instance)
        assert instance._get_weak("test") is instance
        # Ensure that the weak reference was only added to the instance and
        # not its class.
        assert not self._TestClass._get_weak("test")
        instance._del_weak("test")
        assert not instance._get_weak("test")
        del instance
        gc.collect()

    def test_weak_ref_one_way(self):
        """Test linking an object to another through a weak property."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.count == 2
        one.weak_ref = two
        assert one.weak_ref is two
        del two
        gc.collect()
        assert not one.weak_ref
        assert self._TestClass.count == 1
        del one
        gc.collect()
        assert self._TestClass.count == 0

    def test_weak_ref_both_ways(self):
        """Test linking two objects to each other through weak properties."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.count == 2
        one.weak_ref = two
        two.weak_ref = one
        assert one.weak_ref is two and two.weak_ref is one
        del one
        del two
        gc.collect()
        assert self._TestClass.count == 0

    def test_weak_ref_to_self(self):
        """Test linking an object to itself through a weak property."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        assert self._TestClass.count == 1
        one.weak_ref = one
        assert one.weak_ref is one
        del one
        gc.collect()
        assert self._TestClass.count == 0


class TestHasParent:

    """A collection of tests for parents mix-in class."""

    class _A(HasParent):
        pass

    class _B(_A):
        pass

    class _C(_B):
        pass

    class _D:
        pass

    class _E(_D, _C):
        pass

    class _F(_E, _B):
        pass

    def test_get_lineage(self):
        """Test that we can get an objects lineage through the parents."""
        assert (tuple(self._C.get_lineage()) ==
                (self._C, self._B, self._A))
        assert (tuple(self._E.get_lineage()) ==
                (self._E, self._C, self._B, self._A))

    def test_get_lineage_higher_priority(self):
        """Test that we can get the higher priority objects in a lineage."""
        assert (tuple(self._C.get_lineage(priority=1)) == ())

    def test_get_lineage_lower_priority(self):
        """Test that we can get the lower priority objects in a lineage."""
        assert (tuple(self._C.get_lineage(priority=-1)) ==
                (self._B, self._A))

    def test_get_lineage_parent_first(self):
        """Test that we can get an objects lineage with a parent first flag."""
        self._C.parent_first = True
        assert (tuple(self._C.get_lineage()) ==
                (self._B, self._A, self._C))
        assert (tuple(self._C.get_lineage(priority=1)) ==
                (self._B, self._A))
        assert (tuple(self._C.get_lineage(priority=-1)) == ())
        self._E.parent_first = True
        assert (tuple(self._E.get_lineage()) ==
                (self._B, self._A, self._C, self._E))

    def test_get_ancestors(self):
        """Test that we can get the ancestors of an object."""
        assert (tuple(self._C.get_ancestors()) ==
                (self._B, self._A))
        assert tuple(self._A.get_ancestors()) == ()
        assert (tuple(self._F.get_ancestors()) ==
                (self._E, self._C, self._B, self._A))

    def test_has_ancestor(self):
        """Test that we can see if an object has an ancestor."""
        assert self._C.has_ancestor(self._A)
        assert not self._A.has_ancestor(self._C)
