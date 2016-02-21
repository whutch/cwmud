# -*- coding: utf-8 -*-
"""Terrain types and management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from os.path import exists, join

from ... import BASE_PACKAGE
from ...core.attributes import Unset
from ...core.entities import Attribute
from ...core.events import EVENTS
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


TERRAIN.register(Terrain("snm", "Snow-capped Mountains", "^W^^"))
TERRAIN.register(Terrain("mop", "Mountain Peak", "^w^^"))
TERRAIN.register(Terrain("mou", "Mountain Range", "^K^^"))
TERRAIN.register(Terrain("hil", "Rolling Hills", "^yn"))
TERRAIN.register(Terrain("for", "Forest", "^Gt",
                                diversity_name="Dense Forest",
                                diversity_symbol="^gt",
                                diversity_minimum=0.3))
TERRAIN.register(Terrain("gra", "Grasslands", "^G\"",
                                diversity_name="Tall Grass",
                                diversity_symbol="^g\"",
                                diversity_minimum=0.3))
TERRAIN.register(Terrain("bea", "Sandy Beach", "^Y."))
TERRAIN.register(Terrain("shw", "Shallow Water", "^C,"))
TERRAIN.register(Terrain("dpw", "Deep Water", "^c,"))
TERRAIN.register(Terrain("sea", "Open Sea", "^B~"))
TERRAIN.register(Terrain("oce", "Open Ocean", "^b~"))

TERRAIN.register(Terrain("arp", "Arid Mountain Peak", "^k^^"))
TERRAIN.register(Terrain("bmo", "Barren Mountains", "^y^^"))
TERRAIN.register(Terrain("dun", "Sand Dunes", "^Yn"))
TERRAIN.register(Terrain("des", "Desert", "^Y~"))
TERRAIN.register(Terrain("bhi", "Barren Hills", "^wn"))
TERRAIN.register(Terrain("bar", "Barren Land", "^y."))
TERRAIN.register(Terrain("swa", "Swamp", "^G."))
TERRAIN.register(Terrain("mar", "Marshland", "^c&"))
TERRAIN.register(Terrain("whi", "Wooded Hills", "^gn"))
TERRAIN.register(Terrain("wmo", "Wooded Mountains", "^g^^"))
TERRAIN.register(Terrain("mud", "Muddy Fields", "^y\""))
TERRAIN.register(Terrain("jun", "Dense Jungle", "^G%"))
TERRAIN.register(Terrain("jhi", "Jungle Hills", "^Gn"))
TERRAIN.register(Terrain("jmo", "Jungle Mountains", "^c^^"))


@EVENTS.hook("server_boot", "parse_terrain_grid")
def _hook_server_boot():
    _parse_terrain_grid()
