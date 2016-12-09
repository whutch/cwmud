# -*- coding: utf-8 -*-
"""Terrain types and management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os.path import dirname, exists, join

from ...core.attributes import Unset
from ...core.entities import Attribute
from ...core.logs import get_logger
from ...core.utils.exceptions import AlreadyExists
from ...core.world import Room


log = get_logger("worldgen")


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

    def register(self, terrain):
        """Register a terrain type by it's three letter code.

        :param Terrain terrain: The terrain type to register
        :returns None:
        :raises AlreadyExists: If a terrain with `code` is already registered
        :raises TypeError: If `terrain` is not an instance of Terrain
        :raises ValueError: If `code` is not a three letter string

        """
        code = terrain.code
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

    def get_terrain_for_point(self, elevation, moisture, temperature):
        """Get the terrain type for the given point data.

        :param float elevation: The elevation value, from -1 to 1
        :param float moisture: The moisture value, from -1 to 1
        :param float temperature: The temperature value, from -1 to 1
        :returns Terrain: The terrain type or None if not found

        """
        elevation = round(elevation, 1)
        moisture = round(moisture, 1)
        temperature = round(temperature, 1)
        return self._point_table.get((elevation, moisture, temperature))


TERRAIN = TerrainManager()


class Terrain:

    """A terrain type."""

    def __init__(self, code, room_name, symbol, room_description=Unset,
                 diversity_name=None, diversity_symbol=None,
                 diversity_minimum=None):
        self.code = code
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
    def validate(cls, entity, new_value):
        if not isinstance(new_value, Terrain):
            raise ValueError("Room terrain must be a Terrain instance.")
        return new_value

    @classmethod
    def serialize(cls, entity, value):
        return value.code

    @classmethod
    def deserialize(cls, entity, value):
        return TERRAIN[value]


def _parse_terrain_grid():
    log.info("Loading terrain point values.")
    path = join(dirname(__file__), "terrain_grid.txt")
    if not exists(path):
        raise IOError("cannot find terrain grid file!")
    with open(path) as terrain_grid:
        temperature = -1.0
        for line in terrain_grid.readlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) == 1:
                temperature = float(parts[0])
            elif len(parts) == 22:
                elevation = float(parts[0])
                moisture = -1.0
                for code in parts[1:]:
                    terrain = TERRAIN[code]
                    point = (round(elevation, 1),
                             round(moisture, 1),
                             round(temperature, 1))
                    TERRAIN.set_terrain_for_point(point, terrain)
                    moisture += 0.1
            else:
                if parts[0] == "xxx":
                    continue
                raise ValueError("malformed terrain grid! {}".format(parts))


TERRAIN.register(Terrain("bea", "Sandy Beach", "^Y."))
TERRAIN.register(Terrain("shw", "Shallow Water", "^C,"))
TERRAIN.register(Terrain("dpw", "Deep Water", "^c,"))
TERRAIN.register(Terrain("sea", "Open Sea", "^B~"))
TERRAIN.register(Terrain("oce", "Open Ocean", "^b~"))
TERRAIN.register(Terrain("mud", "Muddy Banks", "^y."))
TERRAIN.register(Terrain("frs", "Frozen Shore", "^c."))

TERRAIN.register(Terrain("aup", "Austere Point", "^KA"))
TERRAIN.register(Terrain("wic", "Windswept Crags", "^w^^"))
TERRAIN.register(Terrain("deh", "Desolate Headlands", "^Kn"))
TERRAIN.register(Terrain("tun", "Bleak Tundra", "^c\""))

TERRAIN.register(Terrain("fri", "Frigid Summit", "^cA"))
TERRAIN.register(Terrain("chc", "Chilled Cliffs", "^c^^"))
TERRAIN.register(Terrain("icd", "Icy Drift", "^c~"))
TERRAIN.register(Terrain("scf", "Snow-covered Fields", "^W\""))

TERRAIN.register(Terrain("glp", "Glacial Peaks", "^CA"))
TERRAIN.register(Terrain("fra", "Frosted Alps", "^C^^"))
TERRAIN.register(Terrain("shi", "Snowy Hillside", "^Wn"))
TERRAIN.register(Terrain("bwo", "Boreal Woods", "^Wt"))

TERRAIN.register(Terrain("arr", "Arid Ridges", "^yA"))
TERRAIN.register(Terrain("dus", "Dusty Mesa", "^y^^"))
TERRAIN.register(Terrain("bsl", "Barren Slopes", "^wn"))
TERRAIN.register(Terrain("dry", "Dry Brush", "^y\""))

TERRAIN.register(Terrain("mop", "Mountain Peak", "^wA"))
TERRAIN.register(Terrain("mou", "Mountain Range", "^K^^"))
TERRAIN.register(Terrain("hil", "Rolling Hills", "^yn"))
TERRAIN.register(Terrain("gra", "Grasslands", "^G\"",
                                diversity_name="Tall Grass",
                                diversity_symbol="^g\"",
                                diversity_minimum=0.3))

TERRAIN.register(Terrain("snm", "Snow-capped Mountains", "^WA"))
TERRAIN.register(Terrain("whi", "Wooded Hills", "^gn"))
TERRAIN.register(Terrain("for", "Sparse Forest", "^Gt",
                                diversity_name="Dense Forest",
                                diversity_symbol="^gt",
                                diversity_minimum=0.3))


_parse_terrain_grid()
