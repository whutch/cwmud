# -*- coding: utf-8 -*-
"""Random world generation."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os.path import exists, join
import re

from .. import BASE_PACKAGE
from ..core.characters import Character, get_movement_strings
from ..core.entities import Attribute, Unset
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
_BASE_MOISTURE_ARGS = {"scale": 200, "seed": 23230}
_MOISTURE_NOISE_ARGS = {"scale": 40, "seed": 23230, "octaves": 3}
_DIVERSITY_NOISE_ARGS = {"scale": 5, "seed": 19578}


# Adjust the validation pattern for room names.
RoomName._valid_chars = re.compile(".+")


class TerrainManager:

    """A manager for terrain types."""

    def __init__(self):
        """Create a new terrain manager."""
        self._terrains = {}
        self._point_table = {}

    def __contains__(self, code):
        return code in self._terrains

    def __getitem__(self, code):
        return self._terrains[code]

    def register(self, code, terrain):
        """Register a terrain type by it's three letter code.

        :param str code: A three letter code for the terrain type
        :param Terrain terrain: The terrain type to register
        :returns None:
        :raises AlreadyExists: If a terrain with `code` is already registered
        :raises TypeError: If `terrain` is not an instance of Terrain
        :raises ValueError: If `code` is not a three letter string

        """
        if not isinstance(code, str) or len(code) != 3:
            raise ValueError("terrain code must be 3 letter string")
        if code in self._terrains:
            raise AlreadyExists(code, self._terrains[code], terrain)
        if not isinstance(terrain, Terrain):
            raise TypeError("must be an instance Terrain to register")
        self._terrains[code] = terrain

    def set_terrain_for_point(self, point_data, terrain):
        """Link point data to a specific terrain.

        Each value in the point data tuple should already be rounded
        to their specific ranges.

        :param point_data: A tuple in the form (elevation, moisture)
        :param terrain: The terrain to link this point data to
        :returns None:
        :raises AlreadyExists: If terrain is already linked to `point_data`

        """
        if point_data in self._point_table:
            raise AlreadyExists(point_data, self._point_table[point_data],
                                terrain)
        self._point_table[point_data] = terrain

    def get_terrain_for_point(self, elevation, moisture):
        """Get the terrain type for the given point data.

        :param float elevation: The elevation value, from -1 to 1
        :param float moisture: The moisture value, from -1 to 1
        :returns Terrain: The terrain type or None if not found

        """
        elevation = round(elevation, 1)
        moisture = round(moisture, 1)
        return self._point_table.get((elevation, moisture))


TERRAIN = TerrainManager()


class Terrain:

    """A terrain type."""

    def __init__(self, room_name, symbol, room_description=Unset,
                 diversity_name=None, diversity_symbol=None,
                 diversity_minimum=None):
        self.room_name = room_name
        self.symbol = symbol
        self.room_description = room_description
        self.diversity_name = diversity_name
        self.diversity_symbol = diversity_symbol
        self.diversity_minimum = diversity_minimum

    def is_diverse(self, diversity_value):
        """Return whether this terrain is diverse at a particular value.

        :param float diversity_value: The diversity value to check against
        :return bool: Whether the terrain is diverse or not

        """
        if self.diversity_minimum is None:
            return False
        return diversity_value >= self.diversity_minimum


@Room.register_attr("terrain")
class RoomTerrain(Attribute):
    """A room's terrain type."""

    @classmethod
    def _validate(cls, new_value, entity=None):
        if not isinstance(new_value, Terrain):
            raise ValueError("Room terrain must be a Terrain instance.")
        return new_value


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
        room = generate_room(to_x, to_y, to_z)
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
                           diversity_layer=None, convert_color=False):
    """Render an ASCII terrain map from raw layer data.

    :param elevation_layer: The elevation layer
    :param moisture_layer: The moisture layer
    :param diversity_layer: Optional, a diversity layer
    :param convert_color: Whether to convert color codes or not
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
    return "\n".join("".join(tile for tile in row) for row in rows)


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


@EVENTS.hook("server_boot", "setup_world")
def _hook_server_boot():
    _parse_terrain_grid()
    room = Room.load("0,0,0", default=None)
    if not room:
        generate_room(0, 0, 0)
        log.warn("Had to generate initial room at 0,0,0.")


def _parse_terrain_grid():
    log.info("Loading terrain point values.")
    path = join(BASE_PACKAGE, "contrib", "worldgen", "terrain_grid.txt")
    if not exists(path):
        raise IOError("cannot find terrain grid file!")
    with open(path) as terrain_grid:
        elevation = 1.0
        while elevation >= -1.0:
            line = terrain_grid.readline()
            fields = line.strip().split()[1:]
            moisture = 1.0
            while moisture >= -1.0:
                code = fields.pop()
                terrain = TERRAIN[code]
                point = (round(elevation, 1), round(moisture, 1))
                TERRAIN.set_terrain_for_point(point, terrain)
                moisture -= 0.1
            elevation -= 0.1


TERRAIN.register("snm", Terrain("Snow-capped Mountains", "^W^^"))
TERRAIN.register("mop", Terrain("Mountain Peak", "^w^^"))
TERRAIN.register("mou", Terrain("Mountain Range", "^K^^"))
TERRAIN.register("hil", Terrain("Rolling Hills", "^yn"))
TERRAIN.register("for", Terrain("Forest", "^Gt",
                                diversity_name="Dense Forest",
                                diversity_symbol="^gt",
                                diversity_minimum=0.3))
TERRAIN.register("gra", Terrain("Grasslands", "^G\"",
                                diversity_name="Tall Grass",
                                diversity_symbol="^g\"",
                                diversity_minimum=0.3))
TERRAIN.register("bea", Terrain("Sandy Beach", "^Y."))
TERRAIN.register("shw", Terrain("Shallow Water", "^C,"))
TERRAIN.register("dpw", Terrain("Deep Water", "^c,"))
TERRAIN.register("sea", Terrain("Open Sea", "^B~"))
TERRAIN.register("oce", Terrain("Open Ocean", "^b~"))

TERRAIN.register("arp", Terrain("Arid Mountain Peak", "^k^^"))
TERRAIN.register("bmo", Terrain("Barren Mountains", "^y^^"))
TERRAIN.register("dun", Terrain("Sand Dunes", "^Yn"))
TERRAIN.register("des", Terrain("Desert", "^Y~"))
TERRAIN.register("bhi", Terrain("Barren Hills", "^wn"))
TERRAIN.register("bar", Terrain("Barren Land", "^y."))
TERRAIN.register("swa", Terrain("Swamp", "^G."))
TERRAIN.register("mar", Terrain("Marshland", "^c&"))
TERRAIN.register("whi", Terrain("Wooded Hills", "^gn"))
TERRAIN.register("wmo", Terrain("Wooded Mountains", "^g^^"))
TERRAIN.register("mud", Terrain("Muddy Fields", "^y\""))
TERRAIN.register("jun", Terrain("Dense Jungle", "^G%"))
TERRAIN.register("jhi", Terrain("Jungle Hills", "^Gn"))
TERRAIN.register("jmo", Terrain("Jungle Mountains", "^c^^"))
