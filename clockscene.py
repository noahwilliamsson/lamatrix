#!/usr/bin/env python
#
# This file implements a simple clock scene displaying the current time.
#
# While it is primarily designed to be run on the host computer, an MCU
# running MicroPython might run it to provide automatic rendering of
# the current time while the host computer is offline.
#
import time
if not hasattr(time, 'ticks_ms'):
	# Emulate https://docs.pycom.io/firmwareapi/micropython/utime.html
	time.ticks_ms = lambda: int(time.time() * 1000)
	time.sleep_ms = lambda x: time.sleep(x/1000.0)

# Local imports
from pixelfont import PixelFont

class ClockScene:
	def __init__(self, display, config):
		self.name = 'Clock'
		self.display = display
		self.font = PixelFont()
		self.button_state = 0
		# delete me
		self.x_pos = 4
		self.y_pos = 0
		self.x_vel = 1
		self.y_vel = 1
		self.step = 0

	def reset(self):
		"""
		Unused in this scene
		"""
		pass

	def input(self, button_id, button_state):
		"""
		Handle button input
		"""
		if button_state == 1:
			self.button_state ^= 1
		elif button_state == 2:
			return False
		return True  # signal that we handled the button

	def render(self, frame, dropped_frames, fps):
		"""
		Render the current time and day of week
		"""
		t0 = time.ticks_ms()
		# This takes 0ms
		print('Rendering frame {} @ {}fps after a delay of {}s, {} dropped frames'.format(frame, fps, 1.*(1+dropped_frames)/fps, dropped_frames))
		display = self.display
		display.clear()

		x_off = 0
		y_off = 0
		(year, month, day, hour, minute, second, weekday, _) = time.localtime()[:8]
		if not self.button_state:
			time_str = '{:02d}:{:02d}'.format(hour, minute)
			if (int(time.ticks_ms() // 100.0) % 10) < 4:
				time_str = time_str.replace(':', ' ')
			x_off = 8
		else:
			time_str = '{:02d}.{:02d}.{:02d}'.format(day, month, year % 100)
			x_off = 2

		t2 = time.ticks_ms()

		alphabet = self.font.alphabet
		font_data = self.font.data
		font_height = self.font.height
		font_width = self.font.width
		for i in range(len(time_str)):
			digit = time_str[i]
			if digit in ':. ' or time_str[i-1] in ':. ':
				# Kludge to compress rendering of colon
				x_off -= 1

			data_offset = alphabet.find(digit)
			if data_offset < 0:
				data_offset = 0
			tmp = (data_offset * font_height) << 2  # optimization: multiply by font with
			font_byte = tmp >> 3                    # optimization: divide by number of bits
			font_bit = tmp & 7                      # optimization: modulo number of bits
			for row in range(font_height):
				for col in range(font_width):
					val = 0
					if font_data[font_byte] & (1 << font_bit):
						val = 255
					font_bit += 1
					if font_bit == 8:
						font_byte += 1
						font_bit = 0
					display.put_pixel(x_off+col, y_off+row, val, val, val)
			# Per letter offset
			x_off += 4
		t2 = time.ticks_ms() - t2

		if 0:
			# Flare effect.. lame
			print('Clock: kernel at {},{} to {},{}'.format(self.x_pos, self.y_pos, self.x_pos+1,self.y_pos+1))
			for i in range(3):
				y = self.y_pos+i
				for j in range(6):
					x = self.x_pos+j
					colors = self.display.get_pixel_front(x, y)
					if not sum(colors):
						continue
					if j in [0,1,4,5]:
						c = colors[0]-24
					else:
						c = colors[0]+24
					if c < 0:
						c = 0
					elif c > 255:
						c = 255
					self.display.put_pixel(x, y, c, c, 2*c//3)
			if 1:
				self.x_pos += self.x_vel
				if self.x_pos < 1 or self.x_pos > 31-7:
					self.x_vel *= -1
			if (frame % 3) == 0:
				self.y_pos += self.y_vel
				if self.y_pos == 0 or self.y_pos >= 5:
					self.y_vel *= -1


		t3 = time.ticks_ms()
		x_off = 2
		for i in range(7):
			color = 128 if i == weekday else 48
			x = x_off + (i << 2)
			display.put_pixel(x+0, 7, color, color, 2*color//5)
			display.put_pixel(x+1, 7, color, color, 2*color//5)
			display.put_pixel(x+2, 7, color, color, 2*color//5)
		t3 = time.ticks_ms() - t3

		t4 = time.ticks_ms()
		display.render()
		t4 = time.ticks_ms() - t4
		print('ClockScene: Spent {}ms plotting time, {}ms plotting weekdays, {}ms updating LedMatrix+HAL, {}ms total'.format(t2, t3, t4, time.ticks_ms()-t0))

		if self.button_state == 2:
			self.button_state = 0

		# Signal that we want to be continued to be rendered
		return True
