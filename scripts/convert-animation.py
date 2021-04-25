#!/usr/bin/env python

import sys
import json
import struct

if len(sys.argv) < 2:
	print('Usage: {} <input.json>'.format(sys.argv[0]))
	sys.exit(0)

for filename in sys.argv[1:]:
	f = open(filename)
	obj = json.loads(f.read())
	f.close()
	obj = json.loads(obj['body'])

	out_filename = '.'.join(filename.split('.')[:-1]) + '.bin'
	f = open(out_filename, 'wb')
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
	f.close()
	print('Created {} from {}'.format(out_filename, filename))
