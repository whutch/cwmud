# -*- coding: utf-8 -*-
"""Weather pattern generation."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import time

from ...core.random import generate_noise


class WeatherPattern:

    """A weather pattern."""

    def __init__(self, time_source=time.time, time_scale=1.0, seed=None,
                 formation_speed=1.0, storm_scale=60, wind_scale=None):
        """Create a new weather pattern.

        :param callable time_source: A callable source of time
        :param time_scale: A multiplier to scale time by
        :param seed: A seed to use for the pattern's noise generation
        :param formation_speed: The speed at which storm formations change;
                                higher numbers are faster, zero will not change
        :param storm_scale: The scale of the storm noise
        :param wind_scale: The scale of the wind noise
        :returns None:

        """
        self.time_source = time_source
        self.time_scale = time_scale
        self._time_base = time_source()
        self._time_offset = self._time_base
        self.seed = seed if seed is not None else self._time_base % 100000
        self.formation_speed = formation_speed
        self.storm_scale = storm_scale
        self.wind_scale = wind_scale
        self._offset_x = None
        self._offset_y = None

    @property
    def time_base(self):
        """Return the base time used to generate offsets."""
        return self._time_base

    @property
    def time_offset(self):
        """Return the current time offset."""
        return self._time_offset

    def update(self):
        """Update this weather pattern."""
        self._time_offset = self.time_source() - self._time_base
        self._time_offset *= self.time_scale
        if self.wind_scale is None:
            offset_x = 0
            offset_y = 0
        else:
            offset_x = ((generate_noise(self._time_offset / 10,
                                        self.seed,
                                        scale=self.wind_scale) * 100))
            offset_y = ((generate_noise(self._time_offset / 10,
                                        -self.seed,
                                        scale=self.wind_scale) * 100))
        if self._offset_x is None:
            self._offset_x = (offset_x, offset_x)
        else:
            self._offset_x = (self._offset_x[1], offset_x)
        if self._offset_y is None:
            self._offset_y = (offset_y, offset_y)
        else:
            self._offset_y = (self._offset_y[1], offset_y)

    def get_wind_direction(self):
        """Calculate the direction the wind is currently blowing."""
        if self._offset_x[1] > self._offset_x[0]:
            if self._offset_y[1] > self._offset_y[0]:
                return "SW"
            else:
                return "NW"
        if self._offset_x[1] < self._offset_x[0]:
            if self._offset_y[1] > self._offset_y[0]:
                return "SE"
            else:
                return "NE"
        return "??"

    def get_wind_speed(self):
        """Calculate the current wind speed."""
        x_speed = abs(self._offset_x[1] - self._offset_x[0])
        y_speed = abs(self._offset_y[1] - self._offset_y[0])
        return (x_speed + y_speed) / 2

    def generate_layer(self, width, height, center=(0, 0),
                       octaves=1, persistence=0.5, lacunarity=2.0,
                       fine_noise=None):
        """Generate one layer of weather data using simplex noise.

        :param int width: The width of the weather map
        :param int height: The height of the weather map
        :param tuple(int, int) center: The center of the weather map as (x, y)
        :param int octaves: The number of passes to make calculating noise
        :param float persistence: The amplitude multiplier per octave
        :param float lacunarity: The frequency multiplier per octave
        :param fine_noise: A multiplier for an extra fine noise layer
        :returns: A generated map layer

        """
        formation_shift = self._time_offset * self.formation_speed
        max_x = width // 2
        max_y = height // 2
        rows = []
        offset_x = 0 if self._offset_x is None else self._offset_x[1]
        offset_y = 0 if self._offset_y is None else self._offset_y[1]
        for y in range(center[1] + max_y,
                       center[1] - max_y - (height % 2),
                       -1):
            row = []
            for x in range(center[0] - max_x,
                           center[0] + max_x + (width % 2)):
                storm_noise = generate_noise(x, y, formation_shift, self.seed,
                                             scale=self.storm_scale,
                                             offset_x=offset_x,
                                             offset_y=offset_y,
                                             octaves=octaves,
                                             persistence=persistence,
                                             lacunarity=lacunarity)
                if fine_noise is not None:
                    fine_value = generate_noise(x, y, 0, -self.seed, scale=1)
                    fine_value *= fine_noise
                    row.append(max(-1, min(storm_noise + fine_value, 1)))
                else:
                    row.append(storm_noise)
            rows.append(row)
        return rows
