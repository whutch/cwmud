# -*- coding: utf-8 -*-
"""Terrain types and management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from os.path import exists, join

from ... import BASE_PACKAGE
from ...core.entities import Attribute, Unset
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


@EVENTS.hook("server_boot", "parse_terrain_grid")
def _hook_server_boot():
    _parse_terrain_grid()
