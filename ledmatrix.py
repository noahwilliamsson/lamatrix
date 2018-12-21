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
	rotation = 180
	# Reduce brightness by scaling down colors
	brightness_scaler = 32
	rows = 0
	columns = 0
	driver = None
	fb = []

	def __init__(self, driver, columns = 8, rows = 8, rotation = 0):
		self.driver = driver
		self.columns = columns
		self.rows = rows
		self.num_pixels = rows * columns
		self.num_modified_pixels = self.num_pixels  # optimization: avoid rendering too many pixels
		assert rows == 8, "Calculations in xy_to_phys expect 8 rows"
		self.rotation = (360 + rotation) % 360
		# This is laid out in physical order
		self.fb.append(bytearray(self.num_pixels*3))
		self.fb.append(bytearray(self.num_pixels*3))
		self.fb_index = 0
		# Optimize clear
		self.fb.append(bytearray(self.num_pixels*3))
		for i in range(len(self.fb[0])):
			self.fb[0][i] = 1
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
			x = self.rows-1-y
			y = tmp
		elif self.rotation < 270:
			x = self.columns-1-x
			y = self.rows-1-y
		else:
			tmp = x
			x = y
			y = self.columns-1-tmp
		# The LEDs are laid out in a long string going from north to south,
		# one step to the east, and then south to north, before the cycle
		# starts over.
		#
		# Here we calculate the physical offset for the desired rotation, with
		# the assumption that the first LED is at (0,0).
		# We'll need this adjusting for the north-south-south-north layout
		cycle = self.rows << 1        # optimization: twice the number of rows
		# First we determine which "block" (of a complete cyle) the pixel is in
		nssn_block = x >> 1           # optimization: divide by two
		phys_addr = nssn_block << 4   # optimization: Multiply by cycle
		# Second we determine if the column has decreasing or increasing addrs
		is_decreasing = x & 1
		if is_decreasing:
			phys_addr += cycle - 1 - y
		else:
			phys_addr += y
		return phys_addr

	def phys_to_xy(self, phys_addr):
		"""
		Map physical LED address to x,y after accounting for display rotation
		"""
		x = phys_addr >> 3           # optimization: divide by number of rows
		cycle = self.rows << 1       # optimization: twice the number of rows
		y = phys_addr & (cycle-1)    # optimization: modulo the cycle
		if y >= self.rows:
			y = cycle - 1 - y
		if self.rotation < 90:
			pass
		elif self.rotation < 180:
			tmp = x
			x = self.rows-1-y
			y = tmp
		elif self.rotation < 270:
			x = self.columns-1-x
			y = self.rows-1-y
		else:
			tmp = x
			x = y
			y = self.columns-1-tmp
		return [x, y]

	def get_pixel(self, x, y):
		"""
		Get pixel from the currently displayed frame buffer
		"""
		pixel = self.xy_to_phys(x, y)
		back_index = (self.fb_index+1)%2
		offset = pixel*3
		return [self.fb[back_index][offset+0], self.fb[back_index][offset+1], self.fb[back_index][offset+2]]

	def get_pixel_front(self, x, y):
		"""
		Get pixel from the to-be-displayed frame buffer
		"""
		pixel = self.xy_to_phys(x, y)
		back_index = (self.fb_index)%2
		offset = pixel*3
		return [self.fb[back_index][offset+0], self.fb[back_index][offset+1], self.fb[back_index][offset+2]]

	def put_pixel(self, x, y, r, g, b):
		"""
		Set pixel ni the to-be-displayed frame buffer"
		"""
		if x >= self.columns or y >= self.rows:
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
		self.fb_index ^= 1
		self.fb[self.fb_index][:] = self.fb[2][:]
		# Optimization: keep track of last updated pixel
		self.num_modified_pixels = self.num_pixels

	def render(self):
		"""
		Render the to-be-displayed frame buffer by making put_pixel() and
		render() calls down to the HAL driver.
		"""
		# This takes 11ms
		tX = t0 = time.ticks_ms()
		front = self.fb[self.fb_index]
		back = self.fb[self.fb_index ^ 1]
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
			 	self.driver.put_pixel(pixel, r // self.brightness_scaler, g // self.brightness_scaler, b // self.brightness_scaler)
			 	num_rendered += 1
		t0 = time.ticks_ms() - t0

		# This takes 52ms
		t1 = time.ticks_ms()
		self.driver.update_display(self.num_modified_pixels)
		t1 = time.ticks_ms() - t1
		#time.sleep(0.00004 * self.columns * self.rows)
		#time.sleep_ms(10)

		# This takes 0ms
		self.fb_index ^= 1
		self.fb[self.fb_index][:] = self.fb[self.fb_index^1]
		print('LedMatrix render: {} pixels updated in {}ms, spent {}ms in driver update call, total {}ms'.format(num_rendered, t0, t1, time.ticks_ms() - tX))

		# Optimization: keep track of last updated pixel
		self.num_modified_pixels = 0

	def scrollout(self):
		"""
		Scene transition effect: scroll away pixels
		"""
		for i in range(self.rows):
			for x in range(self.columns):
				self.put_pixel(x, i, 0, 0, 0)
			for y in range(self.rows-1):
				for x in range(self.columns):
					colors = self.get_pixel(x, y)
					self.put_pixel(x, y+1, colors[0], colors[1], colors[2])
			self.render()
			#time.sleep(0.05)
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
		for i in range(self.columns*self.rows):
			colors = self.get_pixel(i % self.columns, i // self.columns)
			if colors[0] or colors[1] or colors[2]:
				active_pixels += 1
		if not active_pixels:
			# No more pixels to dissolve
			return False
		per_pixel_sleep = (0.1-0.00003*self.num_pixels)/active_pixels

		pixel = 1
		for i in range(256):
			bit = pixel & 1
			pixel >>= 1
			if bit:
				pixel ^= 0xb4

			if pixel >= self.columns*self.rows:
				continue
			colors = self.get_pixel(pixel % self.columns, pixel // self.columns)
			if not colors[0] and not colors[1] and not colors[2]:
				continue
			self.put_pixel(pixel % self.columns, pixel // self.columns, 0, 0, 0)
			self.render()
			time.sleep(per_pixel_sleep)
		# There are still pixels to dissolve
		return True
