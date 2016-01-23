# -*- coding: utf-8 -*-
"""Random data generation."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from noise import snoise3


def generate_noise(x, y, scale=1, seed=0, offset_x=0.0, offset_y=0.0,
                   octaves=1, persistence=0.5, lacunarity=2.0,
                   repeat_x=None, repeat_y=None):
    """Generate simplex noise.

    :param x: The x coordinate of the noise value
    :param y: The y coordinate of the noise value
    :param scale: The scale of the base plane
    :param seed: A third dimensional coordinate to use as a seed
    :param float offset_x: How much to offset `x` by on the base plane
    :param float offset_y: How much to offset `y` by on the base plane
    :param int octaves: The number of passes to make calculating noise
    :param float persistence: The amplitude multiplier per octave
    :param float lacunarity: The frequency multiplier per octave
    :param repeat_x: The width of a block of noise to repeat
    :param repeat_y: The height of a block of noise to repeat

    """
    noise_x = (x / scale) + offset_x
    noise_y = (y / scale) + offset_y
    if repeat_x is not None and repeat_y is not None:
        return snoise3(noise_x, noise_y, seed,
                       octaves=octaves,
                       lacunarity=lacunarity,
                       persistence=persistence,
                       repeatx=repeat_x, repeaty=repeat_y)
    else:
        return snoise3(noise_x, noise_y, seed,
                       octaves=octaves,
                       lacunarity=lacunarity,
                       persistence=persistence)
