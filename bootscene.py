from network import WLAN
from machine import RTC
from pixelfont import PixelFont

class BootScene:
	"""
	This module implements a boot scene for Pycom modules
	"""

	def __init__(self, display, config):
		"""
		Initialize the module.
		`display` is saved as an instance variable because it is needed to
		update the display via self.display.put_pixel() and .render()
		"""
		self.display = display
		self.debug = False
		self.intensity = 16
		self.rtc = RTC()
		self.wlan = WLAN()
		if not config:
			return
		if 'debug' in config:
			self.debug = config['debug']
		if 'intensity' in config:
			self.intensity = int(round(config['intensity']*255))

	def reset(self):
		"""
		This method is called before transitioning to this scene.
		Use it to (re-)initialize any state necessary for your scene.
		"""
		pass

	def set_intensity(self, value=None):
		if value is not None:
			self.intensity -= 1
			if not self.intensity:
				self.intensity = 16
		return self.intensity

	def input(self, button_state):
		"""
		Handle button input
		"""
		return 0  # signal that we did not handle the input

	def render(self, frame, dropped_frames, fps):
		"""
		Render the scene.
		This method is called by the render loop with the current frame number,
		the number of dropped frames since the previous invocation and the
		requested frames per second (FPS).
		"""

		dots = str('.' * ((frame % 3) + 1))
		if not self.wlan.isconnected():
			if not frame:
				dots = '?'
			text = 'wifi{}'.format(dots)
		elif not self.rtc.synced():
			text = 'clock{}'.format(dots)
		else:
			text = 'loading'

		display = self.display
		intensity = self.intensity
		display.render_text(PixelFont, text, 1, 1, intensity)
		display.render()
		return True
