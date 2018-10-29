# -*- coding: utf-8 -*-
"""Tools for working with and testing map data."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import sys

from PIL import Image

from cwmud.libs.miniboa import colorize
from cwmud.contrib.worldgen.maps import render_map
from cwmud.contrib.worldgen.terrain import TERRAIN


COLOR_TABLE = {
    "^WA": (250, 250, 250),
    "^W^^": (240, 240, 240),
    "^Wn": (235, 230, 225),
    "^Wt": (245, 225, 200),
    "^W\"": (200, 250, 200),

    "^wA": (180, 180, 180),
    "^w^^": (160, 160, 160),
    "^wn": (100, 100, 10),

    "^KA": (140, 140, 140),
    "^K^^": (120, 120, 120),
    "^Kn": (90, 90, 90),

    "^k^^": (60, 60, 60),

    "^CA": (100, 240, 240),
    "^C^^": (50, 170, 170),
    "^C,": (80, 80, 250),

    "^cA": (15, 130, 115),
    "^c^^": (20, 100, 100),
    "^c&": (45, 150, 45),
    "^c\"": (140, 190, 190),
    "^c~": (130, 190, 210),
    "^c,": (50, 50, 230),
    "^c.": (75, 200, 235),

    "^YA": (160, 160, 15),
    "^Y^^": (180, 180, 20),
    "^Ym": (200, 200, 25),
    "^Y%": (220, 220, 40),
    "^Y~": (240, 240, 60),
    "^Y.": (250, 250, 90),

    "^yA": (75, 75, 0),
    "^y^^": (100, 100, 0),
    "^ym": (150, 150, 0),
    "^yn": (170, 170, 0),
    "^y\"": (140, 100, 50),
    "^y.": (120, 120, 20),

    "^G^^": (50, 80, 20),
    "^Gm": (80, 120, 40),
    "^Gt": (0, 120, 0),
    "^G%": (80, 160, 60),
    "^G\"": (0, 180, 0),
    "^G.": (25, 125, 75),

    "^g^^": (15, 60, 15),
    "^gn": (35, 100, 35),
    "^g&": (0, 80, 0),
    "^gt": (0, 100, 0),
    "^g\"": (0, 160, 0),

    "^B~": (0, 0, 200),
    "^b~": (0, 0, 140),

    "^rA": (75, 0, 0),

    "^": (0, 0, 0),
}


_vis_table = {
    "^r0": (125, 0, 0),
    "^r9": (150, 0, 0),
    "^y8": (125, 125, 0),
    "^y7": (150, 150, 0),
    "^m6": (125, 0, 125),
    "^m5": (150, 0, 150),
    "^b4": (0, 0, 125),
    "^b3": (0, 0, 150),
    "^g2": (0, 125, 0),
    "^g1": (0, 150, 0),
    "^w0": (180, 180, 180),
    "^G1": (0, 200, 0),
    "^G2": (0, 225, 0),
    "^B3": (0, 0, 200),
    "^B4": (0, 0, 225),
    "^M5": (200, 0, 200),
    "^M6": (225, 0, 225),
    "^Y7": (200, 200, 0),
    "^Y8": (225, 225, 0),
    "^R9": (200, 0, 0),
    "^R0": (225, 0, 0),
}


for terrain in TERRAIN._terrains.values():
    if terrain.symbol not in COLOR_TABLE:
        raise ValueError("symbol '{}' not in color table"
                         .format(terrain.symbol))
    if (terrain.diversity_symbol and
            terrain.diversity_symbol not in COLOR_TABLE):
        raise ValueError("symbol '{}' not in color table"
                         .format(terrain.diversity_symbol))


def make_png(path, width, height, center=(0, 0), scale=1.0,
             map_data=None, color_table=None):
    """Create a PNG image from a section of map data.

    :param str path: The path to write the resulting image to
    :param int width: The width of the image to create
    :param int height: The height of the image to create
    :param tuple(int, int) center: The (x, y) coordinate to the
                                   center the map on
    :param float scale: How big the pixels are
    :param map_data: Optional, map data to visualize instead of the default
    :param dict color_table: Optional, a mapping of symbols to colors to use
                             instead of the default
    :returns None:

    """
    if not map_data:
        map_data = render_map(
            width, height, center, join_tiles=False, show_center=False)
    if not color_table:
        color_table = COLOR_TABLE
    pixels = []
    for row in map_data:
        for tile in row:
            pixels.append(color_table[tile])
    image = Image.new("RGB", (width, height))
    image.putdata(pixels, scale=scale)
    image.save(path)


def print_symbols():
    for symbol in "A^wmnu~t%&*\"',.":
        for color in "gGyYwWkKcCbB":
            comp_symbol = "^{}{}".format(
                color, "^^" if symbol == "^" else symbol)
            terrain_name = ""
            for terrain in TERRAIN._terrains.values():
                if (terrain.symbol == comp_symbol or
                            terrain.diversity_symbol == comp_symbol):
                    if terrain_name:
                        print("WARN: duplicate symbol:", terrain.room_name)
                    else:
                        if terrain.symbol == comp_symbol:
                            terrain_name = terrain.room_name
                        else:
                            terrain_name = terrain.diversity_name
            print(colorize("{}^~ - {}".format(comp_symbol, terrain_name)))


if __name__ == "__main__":
    make_png(sys.argv[1], *map(int, sys.argv[2:]))
