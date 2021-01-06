#!/usr/bin/env python
#
# This file provides a small 4x5 (width and height) font primarily designed to
# present the current date and time.
#
# The .data property provides the bits for each character available in .alphabet.
# For each character, the consumer must extract the bits (4x5 == 20 bits) from
# the offset given by the the character's position in .alphabet * 20.
#
# Example:
#
#   font = PixelFont
#   digit = '2'   # Extract and plot the digit '2'
#
#   start_bit = font.alphabet.find(digit) * font.width * font.height
#   font_byte = start_bit // 8
#   font_bit = start_bit % 8
#   for y in range(font.height):
#     for x in range(font.width):
#       is_lit = font.data[font_byte] & (1<<font_bit)
#       put_pixel(x, y, is_lit)
#       font_bit +=1
#       if font_bit == 8:
#         font_byte += 1
#         font_bit = 0
#
# To add new symbols to the font, edit the `font` variable in to_bytearray(),
# add a new 4x5 block representing the symbol, update the .alphabet property
# and then run this file to generate updated data for Python and C:
#
#   $ ./generate-pixelfont.py
#
# Finally update the instance variables in pixelfont.py with the new data.
#

import sys

font_width = 4
font_height = 5
font_alphabet = ' %\'-./0123456789:?acdefgiklmnoprstwxy'

def font_to_bytearray(width, height, alphabet):
###|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|
	font = """
    # #  ##           # ###  #  ### ### # # ### ### ### ### ###     ##   #   #  ##  ### ### ### ### # # #   # # # # ### ### ### ### ### # # # # # # 
      #  ##           # # # ##    #   # # # #   #     # # # # #  #    # # # # # # # #   #   #    #  # # #   ### ### # # # # # # #    #  # # # # # # 
     #       ##      #  # #  #  ###  ## ### ### ###   # ### ###      #  ### #   # # ##  ##  ###  #  ##  #   ### ### # # ### ##  ###  #  ###  #  ### 
    #               #   # #  #  #     #   #   # # #   # # #   #  #      # # # # # # #   #   # #  #  # # #   # # ### # # #   # #   #  #  ### # #  #  
    # #          #  #   ### ### ### ###   # ### ###   # ### ###      #  # #  #  ##  ### #   ### ### # # ### # # # # ### #   # # ###  #  # # # #  #  
""".strip('\n').replace('\n', '')
###|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|

	data = bytearray()
	byte = bits = 0
	num_digits = len(alphabet)
	for i in range(num_digits):
		pixels = bytearray()
		for row in range(height):
			for col in range(width):
				pos = row * num_digits * width
				pos += i * width + col
				is_lit = int(font[pos] != ' ')
				byte |= is_lit << bits
				bits += 1
				if bits == 8:
					data.append(byte)
					bits = byte = 0
	if bits:
		data.append(byte)
	return data

if __name__ == '__main__':
	data = font_to_bytearray(font_width, font_height, font_alphabet)
	debugstr = '12:30 1.8\'c'
	print('Rendering string: {}'.format(debugstr))
	for j in range(len(debugstr)):
		digit = debugstr[j]
		i = font_alphabet.find(digit)
		if i < 0:
			print('WARN: digit {} not found in alphabet'.format(digit))
		font_byte = (i * font_height * font_width) // 8
		font_bit = (i * font_height * font_width) % 8
		for row in range(font_height):
			for col in range(font_width):
				val = 0
				if data[font_byte] & (1 << font_bit):
					val = 255
				sys.stdout.write('#' if val else ' ')
				font_bit += 1
				if font_bit == 8:
					font_byte += 1
					font_bit = 0
			sys.stdout.write('\n')
	print('')
	print('# Computed with pixelfont.py')
	print('width = {}'.format(font_width))
	print('height = {}'.format(font_height))
	print('alphabet = "{}"'.format(font_alphabet))
	print('data = bytearray(b"{}")'.format("".join("\\x{:02x}".format(x) for x in data)))
	print('')
	print('/* Computed with pixelfont.py */')
	print('static int font_width = {};'.format(font_width))
	print('static int font_height = {};'.format(font_height))
	print('static char font_alphabet[] = "{}";'.format(font_alphabet))
	print('static unsigned char font_data[] = "{}";'.format("".join("\\x{:02x}".format(x) for x in data)))
