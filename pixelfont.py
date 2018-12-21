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
#   font = PixelFont()
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
#   $ ./pixelfont.py
#
# Update the variables in the constructor with the new output.
#
class PixelFont:
	def __init__(self):
		self.width = 4
		self.height = 5
		self.alphabet = ' %\'-./0123456789:cms'
		self.data = bytearray("\x00\x00\x50\x24\x51\x66\x00\x00\x60\x00\x00\x00\x42\x24\x11\x57\x55\x27\x23\x72\x47\x17\x77\x64\x74\x55\x47\x74\x71\x74\x17\x57\x77\x44\x44\x57\x57\x77\x75\x74\x20\x20\x20\x15\x25\x75\x57\x75\x71\x74")

	def to_bytearray(self):
###|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|
		font = """
    # #  ##           # ###  #  ### ### # # ### ### ### ### ###      #  # # ### 
      #  ##           # # # ##    #   # # # #   #     # # # # #  #  # # ### #   
     #       ##      #  # #  #  ###  ## ### ### ###   # ### ###     #   ### ### 
    #               #   # #  #  #     #   #   # # #   # # #   #  #  # # # #   # 
    # #          #  #   ### ### ### ###   # ### ###   # ### ###      #  # # ### 
""".strip('\n').replace('\n', '')
###|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|123|

		data = bytearray()
		byte = bits = 0
		num_digits = len(self.alphabet)
		for i in range(num_digits):
			pixels = bytearray()
			for row in range(self.height):
				for col in range(self.width):
					pos = row * num_digits * self.width
					pos += i * self.width + col
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
	import sys

	f = PixelFont()

	data = f.to_bytearray()
	print('')
	print('# Computed with pixelfont.py')
	print('    self.width = {}'.format(f.width))
	print('    self.height = {}'.format(f.height))
	print('    self.alphabet = "{}"'.format(f.alphabet))
	print('    self.data = bytearray("{}")'.format("".join("\\x{:02x}".format(x) for x in data)))
	print('')
	print('/* Computed with pixelfont.py */')
	print('static int font_width = {};'.format(f.width))
	print('static int font_height = {};'.format(f.height))
	print('static char font_alphabet[] = "{}";'.format(f.alphabet))
	print('static unsigned char font_data[] = "{}";'.format("".join("\\x{:02x}".format(x) for x in data)))

	debugstr = '12:30 1.8\'c'
	for j in range(len(debugstr)):
		digit = debugstr[j]
		i = f.alphabet.find(digit)
		if i < 0:
			print('WARN: digit {} not found in alphabet'.format(digit))
		font_byte = (i * f.height * f.width) // 8
		font_bit = (i * f.height * f.width) % 8
		for row in range(f.height):
			for col in range(f.width):
				val = 0
				if data[font_byte] & (1 << font_bit):
					val = 255
				sys.stdout.write('#' if val else ' ')
				font_bit += 1
				if font_bit == 8:
					font_byte += 1
					font_bit = 0
			sys.stdout.write('\n')
