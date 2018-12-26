# This file implements high-level routines for using a LED matrix as a display.
#
# While this code is primarily designed to be running on the host computer,
# MCUs running MicroPython will run this code as well to provide automatic
# rendering of the current time while the host computer is offline.
#
# The constructor needs to be called with a HAL (Hardware Abstraction Layer)
# driver which provides low-level access to the display.  The HAL can be
# e.g. a driver that implements a serial protocol running on an MCU.
#
import time
if not hasattr(time, 'ticks_ms'):
	# Emulate https://docs.pycom.io/firmwareapi/micropython/utime.html
	time.ticks_ms = lambda: int(time.time()*1000)

class LedMatrix:
	def __init__(self, driver, config):
		self.driver = driver
		self.debug = False
		self.stride = 8
		self.columns = 32
		self.rotation = 0
		self.fps = 10
		self.fix_r = 0xff
		self.fix_g = 0xff
		self.fix_b = 0xc0
		if config:
			if 'debug' in config:
				self.debug = config['debug']
			if 'stride' in config:
				self.stride = config['stride']
			if 'columns' in config:
				self.columns = config['columns']
			if 'rotation' in config:
				self.rotation = (360 + config['rotation']) % 360
			if 'fps' in config:
				self.fps = config['fps']
		self.num_pixels = self.stride * self.columns
		# For avoiding multiplications and divisions
		self.num_modified_pixels = self.num_pixels  # optimization: avoid rendering too many pixels
		# This is laid out in physical order
		self.fb = [
			bytearray(self.num_pixels*3),
			bytearray(self.num_pixels*3),
		]
		self.fb_index = 0
		# Initialize display
		self.driver.init_display(self.num_pixels)

	def xy_to_phys(self, x, y):
		"""
		Map x,y to physical LED address after accounting for display rotation
		"""
		if self.rotation < 90:
			pass
		elif self.rotation < 180:
			tmp = x
			x = self.stride-1-y
			y = tmp
		elif self.rotation < 270:
			x = self.columns-1-x
			y = self.stride-1-y
		else:
			tmp = x
			x = y
			y = self.columns-1-tmp
		# The LEDs are laid out in a long string going from north to south,
		# one step to the east, and then south to north, before the cycle
		# starts over.
		stride = self.stride
		phys_addr = x*stride
		if x & 1:
			phys_addr += stride - 1 - y
		else:
			phys_addr += y
		return phys_addr

	def get_pixel(self, x, y):
		"""
		Get pixel from the currently displayed frame buffer
		"""
		pixel = self.xy_to_phys(x, y)
		fb_id = (self.fb_index+1)%2
		offset = pixel*3
		return [self.fb[fb_id][offset+0], self.fb[fb_id][offset+1], self.fb[fb_id][offset+2]]

	def get_pixel_front(self, x, y):
		"""
		Get pixel from the to-be-displayed frame buffer
		"""
		pixel = self.xy_to_phys(x, y)
		fb_id = (self.fb_index)%2
		offset = pixel*3
		return [self.fb[fb_id][offset+0], self.fb[fb_id][offset+1], self.fb[fb_id][offset+2]]

	def put_pixel(self, x, y, r, g, b):
		"""
		Set pixel ni the to-be-displayed frame buffer"
		"""
		if x > self.columns:
			# TODO: proper fix for 16x16 displays
			x -= self.stride
			y += 8
		if x >= self.columns or y >= self.stride:
			return
		pixel = self.xy_to_phys(x, y)
		offset = pixel*3
		self.fb[self.fb_index][offset+0] = int(r)
		self.fb[self.fb_index][offset+1] = int(g)
		self.fb[self.fb_index][offset+2] = int(b)
		# Optimization: keep track of last updated pixel
		if pixel >= self.num_modified_pixels:
			self.num_modified_pixels = pixel+1

	def clear(self):
		"""
		Clear the frame buffer by setting all pixels to black
		"""
		buf = self.fb[self.fb_index]
		for i in range(self.num_pixels*3):
			buf[i] = 0
		self.num_modified_pixels = self.num_pixels

	def render_block(self, data, rows, cols, x, y):
		"""
		Put a block of data of rows*cols*3 size at (x,y)
		"""
		if x+cols > self.columns or y+rows > self.stride:
			return
		offset = 0
		for row in range(rows):
			for col in range(cols):
				self.put_pixel(x+col, y+row, data[offset], data[offset+1], data[offset+2])
				offset += 3

	def render_text(self, font, text, x_off, y_off, intensity=32):
		"""
		Render text with the pixel font
		"""
		put_pixel_fn = self.put_pixel
		w = font.width
		h = font.height
		alphabet = font.alphabet
		font_data = font.data
		in_r = self.fix_r * intensity // 255
		in_g = self.fix_g * intensity // 255
		in_b = self.fix_b * intensity // 255
		low_r = in_r >> 1
		low_g = in_g >> 1
		low_b = in_b >> 1
		for i in range(len(text)):
			digit = text[i]
			if digit in '.:-\' ' or (i and text[i-1] in '.: '):
				x_off -= 1
			data_offset = alphabet.find(digit)
			if data_offset < 0:
				data_offset = 0
			tmp = data_offset * w * h
			font_byte = tmp >> 3
			font_bit = tmp & 7
			for row in range(h):
				for col in range(w):
					if font_data[font_byte] & (1<<font_bit):
						put_pixel_fn(x_off+col, y_off+row, in_r, in_g, in_b)
					else:
						put_pixel_fn(x_off+col, y_off+row, 0, 0, 0)
					font_bit += 1
					if font_bit == 8:
						font_byte += 1
						font_bit = 0
			if digit == 'm':
				put_pixel_fn(x_off+1, y_off+1, low_r, low_g, low_b)
			elif digit == 'w':
				put_pixel_fn(x_off+1, y_off+3, low_r, low_g, low_b)
			elif digit == 'n':
				put_pixel_fn(x_off, y_off+3, low_r, low_g, low_b)
				put_pixel_fn(x_off+2, y_off+1, low_r, low_g, low_b)
			x_off += w

	def render(self):
		"""
		Render the to-be-displayed frame buffer by making put_pixel() and
		render() calls down to the HAL driver.
		"""
		# This takes 11ms
		tX = t0 = time.ticks_ms()
		front = self.fb[self.fb_index]
		back = self.fb[self.fb_index ^ 1]
		put_pixel = self.driver.put_pixel
		num_rendered = 0
		for pixel in range(self.num_modified_pixels):
			# This crap saves about 4ms
			i = pixel*3
			j = i+1
			k = j+1
			r = front[i]
			g = front[j]
			b = front[k]
			if r != back[i] or g != back[j] or b != back[k]:
				put_pixel(pixel, r, g, b)
				num_rendered += 1

		t1 = time.ticks_ms()
		t0 = t1 - t0

		# This takes 52ms
		self.driver.update_display(self.num_modified_pixels)
		t2 = time.ticks_ms()
		t1 = t2 - t1

		# This takes 0ms
		self.fb_index ^= 1
		self.fb[self.fb_index][:] = self.fb[self.fb_index^1]
		# Optimization: keep track of last updated pixel
		self.num_modified_pixels = 0
		if self.debug:
			print('LedMatrix render: {} driver.put_pixel() in {}ms, spent {}ms in driver.update_display(), total {}ms'.format(num_rendered, t0, t1, t2 - tX))

	def hscroll(self, distance=4):
		"""
		Scroll away pixels, left or right
		"""
		if distance > 0:
			z_start, z_end, delta = 0, self.columns, -1
		else:
			z_start, z_end, delta = self.columns-1, -1, 1
		if self.columns % distance:
			distance -= delta
		for zero_lane in range(z_start, z_end, distance):
			fb_cur = self.fb[self.fb_index^1]
			fb_next = self.fb[self.fb_index]
			for y in range(self.stride):
				for x in range(z_end+delta, zero_lane+distance+delta, delta):
					src = self.xy_to_phys(x-distance, y)*3
					dst = self.xy_to_phys(x, y)
					if dst >= self.num_modified_pixels:
						self.num_modified_pixels = dst+1
					dst *= 3
					fb_next[dst] = fb_cur[src]
					fb_next[dst+1] = fb_cur[src+1]
					fb_next[dst+2] = fb_cur[src+2]
			for y in range(self.stride):
				for x in range(zero_lane, zero_lane+distance, -delta):
					dst = self.xy_to_phys(x, y)
					if dst >= self.num_modified_pixels:
						self.num_modified_pixels = dst+1
					dst *= 3
					fb_next[dst] = fb_next[dst+1] = fb_next[dst+2] = 0
			self.render()

	def vscroll(self, distance=2):
		"""
		Scroll away pixels, up or down
		"""
		if distance > 0:
			z_start, z_end, delta = 0, self.stride, -1
		else:
			z_start, z_end, delta = self.stride-1, -1, 1
		if self.stride % distance:
			distance -= delta
		for zero_lane in range(z_start, z_end, distance):
			fb_cur = self.fb[self.fb_index^1]
			fb_next = self.fb[self.fb_index]
			for y in range(z_end+delta, zero_lane+distance+delta, delta):
				for x in range(self.columns):
					src = self.xy_to_phys(x, y-distance)*3
					dst = self.xy_to_phys(x, y)
					if dst >= self.num_modified_pixels:
						self.num_modified_pixels = dst+1
					dst *= 3
					fb_next[dst] = fb_cur[src]
					fb_next[dst+1] = fb_cur[src+1]
					fb_next[dst+2] = fb_cur[src+2]
			for y in range(zero_lane, zero_lane+distance, -delta):
				for x in range(self.columns):
					dst = self.xy_to_phys(x, y)
					if dst >= self.num_modified_pixels:
						self.num_modified_pixels = dst+1
					dst *= 3
					fb_next[dst] = fb_next[dst+1] = fb_next[dst+2] = 0
			self.render()
		return False

	def fade(self):
		"""
		Scene transition effect: fade out active pixels
		"""
		while True:
			light = 0
			for i in range(self.num_pixels):
				colors = self.get_pixel(i % self.columns, i // self.columns)
				colors[0] = colors[0] >> 2
				colors[1] = colors[1] >> 2
				colors[2] = colors[2] >> 2
				light |= colors[0]+colors[1]+colors[2]
				self.put_pixel(i % self.columns, i // self.columns, colors[0], colors[1], colors[2])
			self.render()
			time.sleep(0.1)
			if not light:
				# Everything has faded out
				return False

	def dissolve(self):
		"""
		Scene transition effect: dissolve active pixels with LFSR
		"""
		active_pixels = 0
		for y in range(self.stride):
			for x in range(self.columns):
				colors = self.get_pixel(x, y)
				if colors[0] or colors[1] or colors[2]:
					active_pixels += 1
		if not active_pixels:
			return False

		pixel = 1
		for i in range(256):
			bit = pixel & 1
			pixel >>= 1
			if bit:
				pixel ^= 0xb4
			x, y = pixel % self.columns, pixel // self.columns
			colors = self.get_pixel(x, y)
			if not colors[0] and not colors[1] and not colors[2]:
				continue
			self.put_pixel(x, y, 0, 0, 0)
			if i % 4 == 3:
				self.render()
		# There are still pixels to dissolve
		return True
