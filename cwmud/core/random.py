# -*- coding: utf-8 -*-
"""Random data generation."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import noise


def generate_noise(x, y=0, z=None, w=None, scale=1, offset_x=0.0, offset_y=0.0,
                   octaves=1, persistence=0.5, lacunarity=2.0):
    """Generate simplex noise.

    :param x: The x coordinate of the noise value
    :param y: The y coordinate of the noise value
    :param z: The z coordinate of the noise value
    :param w: A fourth dimensional coordinate
    :param scale: The scale of the base plane
    :param float offset_x: How much to offset `x` by on the base plane
    :param float offset_y: How much to offset `y` by on the base plane
    :param int octaves: The number of passes to make calculating noise
    :param float persistence: The amplitude multiplier per octave
    :param float lacunarity: The frequency multiplier per octave

    """
    x = (x + offset_x) / scale
    y = (y + offset_y) / scale
    if z is not None:
        z /= scale
    if w is not None:
        w /= scale
    if z is None and w is None:
        return noise.snoise2(x, y, octaves=octaves,
                             lacunarity=lacunarity,
                             persistence=persistence)
    elif w is None:
        return noise.snoise3(x, y, z, octaves=octaves,
                             lacunarity=lacunarity,
                             persistence=persistence)
    else:
        return noise.snoise4(x, y, z, w, octaves=octaves,
                             lacunarity=lacunarity,
                             persistence=persistence)
