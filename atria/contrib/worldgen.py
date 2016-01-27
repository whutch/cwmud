# -*- coding: utf-8 -*-
"""Random world generation."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from ..core.characters import Character, get_movement_strings
from ..core.entities import Unset
from ..core.events import EVENTS
from ..core.logs import get_logger
from ..core.random import generate_noise
from ..core.utils.decorators import patch
from ..core.utils.exceptions import AlreadyExists
from ..core.world import Room, RoomName
from ..libs.miniboa import colorize


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

# Noise generation arguments for map layers
_BASE_ELEVATION_ARGS = {"scale": 100, "seed": 15051}
_ELEVATION_NOISE_ARGS = {"scale": 20, "seed": 15051, "octaves": 3}


# Adjust the validation pattern for room names.
RoomName._valid_chars = re.compile(".+")


class TerrainManager:

    """A manager for terrain types."""

    def __init__(self):
        """Create a new terrain manager."""
        self._terrains = {}
        self._table = {}

    def __contains__(self, terrain):
        return terrain in self._terrains

    def __getitem__(self, terrain):
        return self._terrains[terrain]

    def _update_terrain_table(self):
        self._table.clear()
        elevations = sorted([(terrain.min_elevation, terrain)
                             for terrain in self._terrains.values()])
        for index, (elevation, terrain) in enumerate(elevations):
            next_elevation = (elevations[index + 1][0]
                              if index < len(elevations) - 1
                              else 1.01)
            step = elevation
            while step < next_elevation:
                self._table[step] = terrain
                step = round(step + 0.01, 2)

    def register(self, terrain, *more):
        """Register one or more terrain types.

        The internal elevation/moisture table will be updated after
        registration. You can register multiple terrain types at once to
        avoid unnecessary table updates.

        :param Terrain terrain: The terrain type to register
        :param iterable<Terrain> more: Optional, additional terrain types
        :returns None:
        :raises AlreadyExists: If any of the terrain types are already
                               registered
        :raises TypeError: If `terrain` is not an instance of Terrain

        """
        terrains = [terrain] + list(more)
        for terrain in terrains:
            if not isinstance(terrain, Terrain):
                raise TypeError("must be an instance Terrain to register")
            if terrain.name in self._terrains:
                raise AlreadyExists(terrain.name,
                                    self._terrains[terrain.name], terrain)
        for terrain in terrains:
            self._terrains[terrain.name] = terrain
        self._update_terrain_table()

    def get_terrain(self, elevation):
        """Get the terrain type for the given map data.

        :param float elevation: The elevation value, between -1 and 1
        :returns Terrain: The terrain type

        """
        elevation = round(elevation, 2)
        return self._table.get(elevation)


class Terrain:

    """A terrain type."""

    def __init__(self, name, symbol, min_elevation):
        self.name = name
        self.symbol = symbol
        self.min_elevation = min_elevation


TERRAIN = TerrainManager()
TERRAIN.register(Terrain("high mountain", "^W^^", 0.85),
                 Terrain("mountain", "^K^^", 0.75),
                 Terrain("hill", "^yn", 0.65),
                 Terrain("dense forest", "^gt", 0.55),
                 Terrain("forest", "^Gt", 0.40),
                 Terrain("dense grassland", "^g\"", 0.30),
                 Terrain("grassland", "^G\"", 0.00),
                 Terrain("beach", "^Y.", -0.10),
                 Terrain("shallow water", "^C,", -0.25),
                 Terrain("deep water", "^c,", -0.45),
                 Terrain("sea", "^B~", -0.65),
                 Terrain("ocean", "^b~", -1.00))


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
    _map = render_map(MAP_SMALL_WIDTH, MAP_SMALL_HEIGHT, (room.x, room.y))
    self.session.send(_map, "^~", sep="")
    if room.description:
        self.session.send("^m  ", room.description, "^~", sep="")
    if char_list:
        self.session.send(char_list, "^~", sep="")


@patch(Character)
def move_direction(self, x=0, y=0, z=0):
    """Move this character to the room in a given direction.

    :param int x: The change in the X coordinate
    :param int y: The change in the Y coordinate
    :param int z: The change in the Z coordinate
    :returns None:

    """
    if not x and not y and not z:
        # They apparently don't want to go anywhere..
        return
    if not self.room:
        # Can't move somewhere from nowhere.
        return
    to_x, to_y, to_z = map(sum, zip(self.room.coords, (x, y, z)))
    to_coords = "{},{},{}".format(to_x, to_y, to_z)
    room = Room.load(to_coords, default=None)
    if not room:
        room = Room.generate(to_coords, "A Room at {},{}".format(to_x, to_y),
                             description=Unset)
    to_dir, from_dir = get_movement_strings((x, y, z))
    self.move_to_room(room, "{s} move{ss} {dir}.",
                      "{s} arrives from {dir}.",
                      {"dir": to_dir}, {"dir": from_dir})


def generate_room(x, y, z):
    """Generate a single room at the given coordinates.

    :param int x: The room's x coordinate
    :param int y: The room's y coordinate
    :param int z: The room's z coordinate
    :returns world.Room: The generated room

    """
    room = Room({"x": x, "y": y, "z": z})
    room.name = "A Room at {},{}".format(x, y)
    room.description = Unset
    return room


def generate_map_layer(width, height, center=(0, 0), scale=1, seed=0,
                       offset_x=0.0, offset_y=0.0, octaves=1,
                       persistence=0.5, lacunarity=2.0,
                       repeat_x=None, repeat_y=None):
    """Generate one layer of map data using simplex noise.

    :param int width: The width of the map
    :param int height: The height of the map
    :param tuple(int, int) center: The center of the map in (x, y) form
    :param scale: The scale of the base plane
    :param seed: A third dimensional coordinate to use as a seed
    :param float offset_x: How much to offset `x` by on the base plane
    :param float offset_y: How much to offset `y` by on the base plane
    :param int octaves: The number of passes to make calculating noise
    :param float persistence: The amplitude multiplier per octave
    :param float lacunarity: The frequency multiplier per octave
    :param repeat_x: The width of a block of noise to repeat
    :param repeat_y: The height of a block of noise to repeat
    :returns: A generated map layer

    """
    max_x = width // 2
    max_y = height // 2
    rows = []
    for y in range(center[1] + max_y, center[1] - max_y - (height % 2), -1):
        row = []
        for x in range(center[0] - max_x, center[0] + max_x + (width % 2)):
            row.append(generate_noise(x, y, scale=scale, seed=seed,
                                      offset_x=offset_x, offset_y=offset_y,
                                      octaves=octaves,
                                      persistence=persistence,
                                      lacunarity=lacunarity,
                                      repeat_x=repeat_x, repeat_y=repeat_y))
        rows.append(row)
    return rows


def combine_map_layers(map_layer, *more_layers):
    """Create a new layer of map data by combining multiple layers.

    The result of combining different sizes of map data is undefined.

    :param map_layer: The base layer
    :param iterable more_layers: Additional layers to fold into the base
    :returns: A combined map layer

    """
    new_layer = []
    row_sets = zip(map_layer, *more_layers)
    for row_set in row_sets:
        grouped = zip(*row_set)
        summed = (sum(group) for group in grouped)
        averaged = map(lambda n: n / (1 + len(more_layers)), summed)
        new_layer.append(list(averaged))
    return new_layer


def render_map_from_layers(elevation_layer, convert_color=False):
    """Render an ASCII terrain map from raw layer data.

    :param elevation_layer: The elevation layer
    :param convert_color: Whether to convert color codes or not
    :returns str: A rendered map

    """
    height = len(elevation_layer)
    width = len(elevation_layer[0])
    center = (width // 2, height // 2)
    rows = []
    for y, values in enumerate(elevation_layer):
        row = []
        for x, value in enumerate(values):
            if (x, y) == center:
                row.append("^M#")
            else:
                terrain = TERRAIN.get_terrain(value)
                row.append(terrain.symbol if terrain else "^R?")
        rows.append(row)
    if convert_color:
        for row in rows:
            for index, tile in enumerate(row):
                row[index] = colorize(tile)
    return "\n".join("".join(tile for tile in row) for row in rows)


def render_map(width, height, center=(0, 0), convert_color=False):
    """Render an ASCII terrain map.

    :param int width: The width of the map
    :param int height: The height of the map
    :param tuple(int, int) center: The center of the map in (x, y) form
    :param convert_color: Whether to convert color codes or not
    :returns str: A rendered map

    """
    # Calculate the map data
    base_elevation = generate_map_layer(width, height, center=center,
                                        **_BASE_ELEVATION_ARGS)
    elevation_noise = generate_map_layer(width, height, center=center,
                                         **_ELEVATION_NOISE_ARGS)
    elevation_layer = combine_map_layers(base_elevation, elevation_noise)
    return render_map_from_layers(elevation_layer, convert_color=convert_color)


# Unhook all the default events in the setup_world namespace.
EVENTS.unhook("*", "setup_world")


@EVENTS.hook("server_boot", "setup_world")
def _hook_server_boot():
    room = Room.load("0,0,0", default=None)
    if not room:
        Room.generate("0,0,0", "A Room at 0,0", Unset)
        log.warn("Had to generate initial room at 0,0,0.")
