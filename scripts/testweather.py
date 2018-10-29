
from time import sleep, time
from subprocess import call

from cwmud.contrib.weather.patterns import WeatherPattern
from cwmud.contrib.worldgen.maps import (_render_map_data,
                                         render_map_from_layers)
from cwmud.contrib.worldgen.terrain import _parse_terrain_grid
from cwmud.libs.miniboa import colorize


def _weather_tiles(rain_value, wind_value):
    if -0.03 <= wind_value <= 0.03:
        if rain_value >= 0.7:
            return "^YH"
        else:
            return "^wW"
    else:
        if rain_value >= 0.6:
            return "^CL"
        if rain_value >= 0.4:
            return "^cR"
        if rain_value >= 0.3:
            return "^bR"
    return None


if __name__ == "__main__":
    # Run a visual test of the weather system.
    rain_seed = time() % 10000
    wind_seed = rain_seed / 2
    rain_pattern = WeatherPattern(time_scale=2, formation_speed=0.25,
                                  storm_scale=50, wind_scale=20,
                                  seed=rain_seed)
    wind_pattern = WeatherPattern(time_scale=2, formation_speed=0.35,
                                  storm_scale=100, wind_scale=20,
                                  seed=wind_seed)
    _parse_terrain_grid()
    terrain_map = render_map_from_layers(*_render_map_data(109, 37,
                                                           center=(-100, 100)),
                                         convert_color=False, join_tiles=False)
    while True:
        rain_pattern.update()
        wind_pattern.update()
        rain_data = rain_pattern.generate_layer(109, 37, octaves=2,
                                                fine_noise=0.1)
        wind_data = wind_pattern.generate_layer(109, 37, octaves=2,
                                                fine_noise=0.05)
        call("clear")
        sidebar = ("^MSeed: {:>#9.8}\n^YTime: {:>#6.5g}\n\n"
                   "^BRain Storms:\n"
                   "^GXY: {:=+#8g} {:=+#8g}\n^CMovement: {} @ {:#.4}^~\n\n"
                   "^BWind Storms:\n"
                   "^GXY: {:=+#8g} {:=+#8g}\n^CMovement: {} @ {:#.4}^~\n\n"
                   "^wStorm Legend:\n"
                   "^KLight ^bR^Kain\n^KHeavy ^cR^Kain\n"
                   "^CL^Kightning\n^KStrong ^wW^Kind\n"
                   "^YH^Kurricane Winds!^~"
                   .format(rain_pattern.seed,
                           round(rain_pattern.time_offset, 3),
                           round(rain_pattern._offset_x[1], 3),
                           round(rain_pattern._offset_y[1], 3),
                           rain_pattern.get_wind_direction(),
                           round(rain_pattern.get_wind_speed(), 3),
                           round(wind_pattern._offset_x[1], 3),
                           round(wind_pattern._offset_y[1], 3),
                           wind_pattern.get_wind_direction(),
                           round(wind_pattern.get_wind_speed(), 3))
                   .split("\n"))
        for y in range(len(rain_data)):
            tiles = []
            for x in range(len(rain_data[y])):
                tile = _weather_tiles(rain_data[y][x], wind_data[y][x])
                if tile is None:
                    tile = terrain_map[y][x]
                tiles.append(tile)
            tiles.append("^~")
            row = "".join(tiles)
            if y < len(sidebar):
                row = row + " " + sidebar[y]
            print(colorize(row))
        sleep(0.1)
