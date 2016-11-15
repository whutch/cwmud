# -*- coding: utf-8 -*-
"""Map generation and management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import re

from ...core.characters import Character
from ...core.cmds.cmd_admin import GotoCommand
from ...core.events import EVENTS
from ...core.logs import get_logger
from ...core.random import generate_noise
from ...core.utils.decorators import patch
from ...core.world import Room, RoomName
from ...libs.miniboa import colorize
from .terrain import TERRAIN


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
_BASE_MOISTURE_ARGS = {"scale": 200, "seed": 23230}
_MOISTURE_NOISE_ARGS = {"scale": 40, "seed": 23230, "octaves": 3}
_DIVERSITY_NOISE_ARGS = {"scale": 5, "seed": 19578}


# Adjust the validation pattern for room names.
RoomName._valid_chars = re.compile(".+")


@patch(Room)
def get_exits(self):
    """Return the rooms this room connects to.

    If the neighboring rooms don't exist, they will be created.

    :returns dict: The connecting rooms, keyed by direction name

    """
    # This is an inefficient placeholder until an Exit type is in.
    found = {}
    for change, (dir_name, rev_name) in self._movement_strings.items():
        x, y, z = map(sum, zip(self.coords, change))
        room = Room.get(x=x, y=y, z=z)
        if (not room) and change[2] == 0:  # Don't auto-create "up" and "down"
            room = generate_room(x, y, z)
        if room:
            found[dir_name] = room
    return found


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
    self.session.send("^Y{}^~ ({},{})".format(
        room.name or "A Room", room.x, room.y))
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
    room = Room.get(x=to_x, y=to_y, z=to_z)
    if not room:
        room = generate_room(to_x, to_y, to_z)
    to_dir, from_dir = Room.get_movement_strings((x, y, z))
    self.move_to_room(room, "{s} move{ss} {dir}.",
                      "{s} arrives from {dir}.",
                      {"dir": to_dir}, {"dir": from_dir})


@patch(GotoCommand)
def _action(self):
    try:
        coords = self.args[0].split(",")
        if len(coords) == 2:
            coords.append("0")
        elif len(coords) != 3:
            raise IndexError
        x, y, z = map(int, coords)
        room = Room.get(x=x, y=y, z=z)
        if not room:
            room = generate_room(x, y, z)
        poof_out = "{s} disappear{ss} in a puff of smoke."
        poof_in = "{s} arrive{ss} in a puff of smoke."
        self.session.char.move_to_room(room, poof_out, poof_in)
    except IndexError:
        self.session.send("Syntax: goto (x),(y)[,z]")


def generate_room(x, y, z):
    """Generate a single room at the given coordinates.

    :param int x: The room's x coordinate
    :param int y: The room's y coordinate
    :param int z: The room's z coordinate
    :returns world.Room: The generated room

    """
    room = Room()
    room.x, room.y, room.z = x, y, z
    terrain, diverse = get_terrain_for_coord(x, y)
    room.terrain = terrain
    if diverse and terrain.diversity_symbol:
        room.name = terrain.diversity_name
    else:
        room.name = terrain.room_name
    room.description = terrain.room_description
    return room


def generate_map_layer(width, height, center=(0, 0), scale=1, seed=0,
                       offset_x=0.0, offset_y=0.0, octaves=1,
                       persistence=0.5, lacunarity=2.0):
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
    :returns: A generated map layer

    """
    max_x = width // 2
    max_y = height // 2
    rows = []
    for y in range(center[1] + max_y, center[1] - max_y - (height % 2), -1):
        row = []
        for x in range(center[0] - max_x, center[0] + max_x + (width % 2)):
            row.append(generate_noise(x, y, seed, scale=scale,
                                      offset_x=offset_x, offset_y=offset_y,
                                      octaves=octaves,
                                      persistence=persistence,
                                      lacunarity=lacunarity))
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


def _render_map_data(width, height, center=(0, 0)):
    """Render raw layer data for a rectangle of map.

    :param int width: The width of the map
    :param int height: The height of the map
    :param tuple(int, int) center: The center of the map in (x, y) form
    :returns tuple(layers): A tuple of map layers

    """
    # Calculate the elevation layer
    base_elevation = generate_map_layer(width, height, center=center,
                                        **_BASE_ELEVATION_ARGS)
    elevation_noise = generate_map_layer(width, height, center=center,
                                         **_ELEVATION_NOISE_ARGS)
    elevation_layer = combine_map_layers(base_elevation, elevation_noise)
    # Calculate the moisture layer
    base_moisture = generate_map_layer(width, height, center=center,
                                       **_BASE_MOISTURE_ARGS)
    moisture_noise = generate_map_layer(width, height, center=center,
                                        **_MOISTURE_NOISE_ARGS)
    moisture_layer = combine_map_layers(base_moisture, moisture_noise)
    # Calculate the diversity layer
    diversity_layer = generate_map_layer(width, height, center=center,
                                         **_DIVERSITY_NOISE_ARGS)
    return elevation_layer, moisture_layer, diversity_layer


def render_map_from_layers(elevation_layer, moisture_layer,
                           diversity_layer=None, convert_color=False,
                           join_tiles=True):
    """Render an ASCII terrain map from raw layer data.

    :param elevation_layer: The elevation layer
    :param moisture_layer: The moisture layer
    :param diversity_layer: Optional, a diversity layer
    :param convert_color: Whether to convert color codes or not
    :param join_tiles: Whether to join the tiles into a string
    :returns str: A rendered map

    """
    height = len(elevation_layer)
    width = len(elevation_layer[0])
    center = (width // 2, height // 2)
    rows = []
    for y in range(height):
        values = list(zip(elevation_layer[y], moisture_layer[y]))
        row = []
        for x in range(width):
            if (x, y) == center:
                row.append("^W@")
            else:
                elevation, moisture = values[x]
                terrain = TERRAIN.get_terrain_for_point(elevation, moisture)
                symbol = None
                if not terrain:
                    symbol = "^R?"
                else:
                    if diversity_layer and terrain.diversity_symbol:
                        diversity = diversity_layer[y][x]
                        if terrain.is_diverse(diversity):
                            symbol = terrain.diversity_symbol
                if symbol is None:
                    symbol = terrain.symbol
                row.append(symbol)
        rows.append(row)
    if convert_color:
        for row in rows:
            for index, tile in enumerate(row):
                row[index] = colorize(tile)
    if join_tiles:
        return "\n".join("".join(tile for tile in row) for row in rows) + "^~"
    else:
        return rows


def render_map(width, height, center=(0, 0), convert_color=False):
    """Render an ASCII terrain map.

    :param int width: The width of the map
    :param int height: The height of the map
    :param tuple(int, int) center: The center of the map in (x, y) form
    :param convert_color: Whether to convert color codes or not
    :returns str: A rendered map

    """
    elevation, moisture, diversity = _render_map_data(width, height,
                                                      center=center)
    return render_map_from_layers(elevation, moisture, diversity,
                                  convert_color=convert_color)


def get_terrain_for_coord(x, y):
    """Get the terrain type for a coordinate.

    :param int x: The x coordinate
    :param int y: The y coordinate
    :returns tuple(Terrain, bool): The terrain type and whether it is diverse

    """
    elevation, moisture, diversity = _render_map_data(1, 1, (x, y))
    terrain = TERRAIN.get_terrain_for_point(elevation[0][0], moisture[0][0])
    return terrain, terrain.is_diverse(diversity[0][0])


_VISUALIZE_TABLE = {
    -1.0: "^r0", -0.9: "^r9", -0.8: "^y8", -0.7: "^y7", -0.6: "^m6",
    -0.5: "^m5", -0.4: "^b4", -0.3: "^b3", -0.2: "^g2", -0.1: "^g1",
    0.0: "^w0", 0.1: "^G1", 0.2: "^G2", 0.3: "^B3", 0.4: "^B4", 0.5: "^M5",
    0.6: "^M6", 0.7: "^Y7", 0.8: "^Y8", 0.9: "^R9", 1.0: "^R0",
}


def _visualize_map_layer(map_layer, formatter=None):
    """Print raw, colored map data for visualization.

    :param map_layer: The base layer
    :param callable formatter: Optional, a filter for map data; should accept
                               a value from -1 to 1 rounded to a tenth and
                               return a single printable character
    :returns None:

    """
    rows = []
    for values in map_layer:
        if not formatter or not callable(formatter):
            formatter = lambda value: _VISUALIZE_TABLE[value]
        rows.append("".join([formatter(round(value, 1))
                            for value in values]))
    print(colorize("\n".join(rows)))


# Unhook all the default events in the setup_world namespace.
EVENTS.unhook("*", "setup_world")


@EVENTS.hook("server_boot", "setup_world", after="parse_terrain_grid")
def _hook_server_boot():
    room = Room.get(x=0, y=0, z=0)
    if not room:
        generate_room(0, 0, 0)
        log.warning("Had to generate initial room at 0,0,0.")
