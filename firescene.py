try:
	from uos import urandom
except:
	from os import urandom
from pixelfont import PixelFont

class FireScene:
	"""This module implements an example scene with a traveling pixel"""

	def __init__(self, display, config):
		"""
		Initialize the module.
		`display` is saved as an instance variable because it is needed to
		update the display via self.display.put_pixel() and .render()
		"""
		self.display = display
		self.intensity = 32
		self.remaining_frames = self.display.fps<<2
		if not config:
			return
		if 'intensity' in config:
			self.intensity = int(round(config['intensity']*255))

	def reset(self):
		"""
		This method is called before transitioning to this scene.
		Use it to (re-)initialize any state necessary for your scene.
		"""
		self.remaining_frames = self.display.fps<<2

	def input(self, button_state):
		"""
		Handle button input
		"""
		return 0  # signal that we did not handle the input

	def set_intensity(self, value=None):
		if value is not None:
			self.intensity -= 1
			if not self.intensity:
				self.intensity = 16
		return self.intensity

	def render(self, frame, dropped_frames, fps):
		"""
		Render the scene.
		This method is called by the render loop with the current frame number,
		the number of dropped frames since the previous invocation and the
		requested frames per second (FPS).
		"""

		display = self.display
		get_pixel = display.get_pixel
		put_pixel = display.put_pixel
		intensity = self.intensity
		width = display.columns
		max_y = display.stride - 1

		# Fire source
		b = intensity >> 1
		for x in range(display.columns):
			put_pixel(x, max_y, intensity, intensity, b)

		# Spread fire
		for y in range(max_y):
			for x in range(width):
				# Cool previous pixel
				r, g, b = display.get_pixel(x, y)
				if r or g or b:
					r -= 1
					g -= 1
					b >>= 1
					put_pixel(x, y, max(r, 0), max(g, 0), b)
				# Spread heat from below
				r, g, b = get_pixel(x, y+1)
				try:
					spread = (urandom(1)[0]&3) - 1
				except TypeError:
					spread = (ord(urandom(1)[0])&3) - 1
				r -= spread
				g -= 1
				b >>= 2
				put_pixel(x+spread, y, max(r, 0), max(g, 0), b)

		display.render()
		self.remaining_frames -= 1
		if not self.remaining_frames:
			return False
		return True
