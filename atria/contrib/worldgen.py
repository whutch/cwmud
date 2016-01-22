# -*- coding: utf-8 -*-
"""Random world generation."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from functools import lru_cache
import random
import re

from ..core.characters import Character
from ..core.entities import Attribute, Unset
from ..core.logs import get_logger
from ..core.utils.decorators import patch
from ..core.utils.funcs import joins
from ..core.world import Room, RoomName


log = get_logger("worldgen")


# Settings

# Odd numbers are better for these, as they will have a centered cursor.
MAP_SMALL_WIDTH = 21  # The width of the map viewed in "look"
MAP_SMALL_HEIGHT = 13  # The height of the map viewed in "look"


# Coordinate deltas for each direction, starting east and
# going counter-clockwise (northeast, north, and so on).
_DIRECTION_DELTAS = ((1, 0), (1, -1), (0, -1), (-1, -1),
                     (-1, 0), (-1, 1), (0, 1), (1, 1))

# Mapping of names and descriptions for randomly generated rooms, keyed by
# terrain type tuples in the form (self, east, north, west, south).  If a name
# or description value is a tuple or list of values, a random one is used.
_ROOM_FLAVOR = {

}


@Room.register_attr("elevation")
class RoomElevation(Attribute):

    """The elevation of a room."""

    default = 4
    min = -12
    max = 12

    @classmethod
    def _validate(cls, new_value):
        if not isinstance(new_value, int):
            raise ValueError("Room elevations must be integers.")
        if new_value < cls.min or new_value > cls.max:
            raise ValueError(joins("Room elevations must be between ",
                                   cls.min, " and ", cls.max, ".", sep=""))
        return new_value


@patch(Room)
def choose_elevation(self, base_elevation=RoomElevation.default,
                     change_threshold=1, neighbor_weight=3):
    """Set this room's elevation randomly based on its neighbors.

    :param int base_elevation: The elevation to start with when there are
                               no neighbors to get data from
    :param int change_threshold: How much an elevation can change at once
    :param int neighbor_weight: How much to weigh neighbor elevations over
                                choosing new ones
    :returns None:

    """
    choices = []
    for direction in range(8):
        x_delta, y_delta = _DIRECTION_DELTAS[direction]
        neighbor = Room.load("{},{},{}".format(self.x + x_delta,
                                               self.y + y_delta, 0),
                             default=None)
        if neighbor:
            elevation_min = max(neighbor.elevation - change_threshold,
                                RoomElevation.min)
            elevation_max = min(neighbor.elevation + change_threshold,
                                RoomElevation.max)
            choices.extend(range(elevation_min, elevation_max + 1))
            choices.extend([neighbor.elevation] * (neighbor_weight - 1))
    if choices:
        self.elevation = random.choice(choices)
    else:
        self.elevation = base_elevation


@patch(Character)
def show_room(self, room=None):
    """Show a room's contents to the session controlling this character.

    :param world.Room room: Optional, the room to show to this character;
                            if None, their current room will be shown
    :returns None:

    """
    if not self.session:
        return
    if not room:
        if not self.room:
            return
        room = self.room
    char_list = "\n".join(["^G{} ^g{}^g is here.^~".format(
                           char.name, char.title)
                           for char in room.chars if char is not self])
    self.session.send("^Y", room.name or "A Room", "^~", sep="")
    _map = create_map((room.x, room.y), MAP_SMALL_WIDTH, MAP_SMALL_HEIGHT,
                      auto_fill=True)
    self.session.send(_map, "^~", sep="")
    if room.description:
        self.session.send("^m  ", room.description, "^~", sep="")
    if char_list:
        self.session.send(char_list, "^~", sep="")


@lru_cache(maxsize=None)
def get_terrain_symbol(elevation):
    """Convert an elevation number into an ASCII terrain symbol.

    :param int elevation: The elevation to convert
    :returns str: The converted terrain symbol

    """
    if elevation is None:
        return "^R!"
    if elevation >= 12:
        return '^W^^'
    if elevation >= 10:
        return "^K^^"
    if elevation >= 7:
        return "^yn"
    if elevation >= 6:
        return '^g"'
    if elevation >= 2:
        return '^G"'
    if elevation >= 0:
        return "^Y."
    if elevation >= -3:
        return '^C,'
    if elevation >= -4:
        return "^c,"
    if elevation >= -8:
        return "^B~"
    if elevation >= -12:
        return "^b~"
    return '^R?'


@lru_cache(maxsize=256)  # Remove this cache when maps are not terrain only.
def create_map(center=(0, 0), width=5, height=5, auto_fill=False):
    """Create an ASCII map to be sent to a client.

    :param tuple(int, int) center: The map's center in (x, y) form
    :param int width: The desired map width
    :param int height: The desired map height
    :param bool auto_fill: Whether to automatically generate new rooms to
                           fill any gaps in the map
    :returns str: The created map

    """
    max_x = width // 2
    max_y = height // 2
    rows = []
    for y in range(center[1] + max_y, center[1] - max_y - (height % 2), -1):
        row = []
        for x in range(center[0] - max_x, center[0] + max_x + (width % 2)):
            room = Room.load("{},{},{}".format(x, y, 0), default=None)
            if not room and auto_fill:
                room = generate_room(x, y, 0)
            row.append(get_terrain_symbol(room.elevation) if room else " ")
        if y == center[1]:
            row[max_x] = "^R#"
        rows.append("".join(row))
    return "\n".join(rows)


def generate_room(x, y, z):
    """Generate a single room at the given coordinates.

    :param int x: The room's x coordinate
    :param int y: The room's y coordinate
    :param int z: The room's z coordinate
    :returns world.Room: The generated room

    """
    room = Room({"x": x, "y": y, "z": z})
    room.choose_elevation()
    room.name = "A Room at {},{}".format(x, y)
    room.description = Unset
    return room


def generate_rooms(center=(0, 0), width=3, height=3):
    """Generate a box of new rooms.

    :param tuple(int, int) center: The center of the box in (x, y) form
    :param int width: The width of the box
    :param int height: The height of the box
    :returns None:

    """
    max_x = width // 2
    max_y = height // 2
    for x in range(center[0] - max_x, center[0] + max_x + (width % 2)):
        for y in range(center[1] - max_y, center[1] + max_y + (height % 2)):
            room = Room.load("{},{},{}".format(x, y, 0), default=None)
            if not room:
                generate_room(x, y, 0)


# Adjust the validation pattern for room names.
RoomName._valid_chars = re.compile(".+")
