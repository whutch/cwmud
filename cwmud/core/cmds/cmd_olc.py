# -*- coding: utf-8 -*-
"""Commands for online creation."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from ..characters import CharacterShell
from ..commands import Command, COMMANDS
from ..world import Room


@COMMANDS.register
class DigCommand(Command):

    """A command for creating new rooms."""

    _dirs = {
        "east": (1, 0, 0),
        "west": (-1, 0, 0),
        "north": (0, 1, 0),
        "south": (0, -1, 0),
        "up": (0, 0, 1),
        "down": (0, 0, -1),
    }

    def _action(self):
        char = self.session.char
        if not char.room:
            self.session.send("You're not in a room!")
            return
        for dir_name, change in self._dirs.items():
            if dir_name.startswith(self.args[0]):
                break
        else:
            self.session.send("That's not a direction.")
            return
        x, y, z = map(sum, zip(char.room.coords, change))
        room = Room.find(x=x, y=y, z=z)
        if room:
            self.session.send("There's already a room over there!")
            return
        room = Room()
        room.x, room.y, room.z = x, y, z
        room.save()
        char.move_to_room(room, "{s} tunnel{ss} out a new room to the {dir}!",
                          depart_context={"dir": dir_name})


@COMMANDS.register
class NameCommand(Command):

    """A command for naming things."""

    no_parse = True

    def _action(self):
        # This will later be a general OLC command for naming anything but
        # for now you can just name rooms.
        char = self.session.char
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.room.name = self.args[0].strip().title()
        self.session.send("Ok.")


CharacterShell.add_verbs(DigCommand, "dig")
CharacterShell.add_verbs(NameCommand, "name")
