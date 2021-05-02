#!/usr/bin/env python

import sys
import json
import struct
import requests
import os

from pprint import pprint
from typing import Dict

ICON_URL = "https://developer.lametric.com/api/v1/dev/preloadicons?icon_id={}"
weather_ids = {"sunny": 1338,
               "sunny-with-clouds": 8756,
               "cloud-partly": 2286,
               "cloudy": 12019,
               "fog": 17056,
               "moon-stars": 16310,
               "rain-snow": 160,
               "rain": 72,
               "snow-house": 7075,
               "snowy": 2289,
               "thunderstorm": 11428}

animation_ids = {"game-brick":1524,
                 "game-invaders-1":3405,
                 "game-invaders-2":3407,
                 "game-tetris":4007,
                 "game-nintendo":5038,
                 "game-pacman-ghosts":20117,
                 "game-pingpong":4075,
                 "game-snake":16036,
                 "matrix":653,
                 "newyears":9356,
                 "tv-movie":7862}

def download_and_create_bins(icon_ids: Dict[str, int], dir_name: str):
    for name, icon_id in icon_ids.items():
        r = requests.get(ICON_URL.format(icon_id))
        r_json = r.json()
        obj = json.loads(r_json['body'])

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        out_filename = f"{dir_name}/{name}.bin"
        with open(out_filename, "wb") as f:
            delays = obj['delays']
            icons = obj['icons']

            num_frames = len(icons)
            rows = len(icons[0])
            cols = len(icons[0][0])
            colors = min(len(icons[0][0][0]), 3)
            assert colors == 3, "Number of colors must be 3"

            header = bytearray(4)
            header[0] = num_frames
            header[1] = rows
            header[2] = cols
            header[3] = 3
            f.write(header)
            chunk = bytearray(num_frames * 2)
            for i in range(num_frames):
                struct.pack_into('!h', chunk, i*2, delays[i])
            f.write(chunk)

            for i in range(len(icons)):
                icon = icons[i]
                for y in range(len(icon)):
                    row = icon[y]
                    for x in range(len(row)):
                        column = row[x]
                        for color in range(min(len(column), 3)):
                            f.write(struct.pack('B', int(255*column[color])))

        print('Created {} from {}'.format(out_filename, ICON_URL.format(icon_id)))


download_and_create_bins(icon_ids=weather_ids, dir_name="weather")
download_and_create_bins(icon_ids=animation_ids, dir_name="animations")
