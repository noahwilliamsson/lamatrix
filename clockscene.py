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

# Local imports
from pixelfont import PixelFont


class ClockScene:
	def __init__(self, display, config):
		self.display = display
		self.button_state = 0
		self.debug = False
		self.intensity = 16
		self.date_was_shown = False
		self.columns = display.columns
		if not config:
			return
		if 'debug' in config:
			self.debug = config['debug']
		if 'intensity' in config:
			self.intensity = int(round(config['intensity']*255))

	def reset(self):
		pass

	def input(self, button_state):
		if button_state & 0x22:
			# Handle long-press on either button
			self.button_state ^= 1
			self.display.clear()
			return button_state & ~0x22

		return 0  # signal that we did not handle the button press

	def set_intensity(self, value=None):
		if value is not None:
			self.intensity -= 1
			if not self.intensity:
				self.intensity = 16
		return self.intensity

	def render(self, frame, dropped_frames, fps):
		"""
		Render the current time and day of week
		"""
		display = self.display
		intensity = self.intensity

		# Automatically switch to showing the date for a few secs
		tmp = fps << 6
		tmp = ((fps << 4) + frame) % tmp

		y_off = 1
		(year, month, day, hour, minute, second, weekday, _) = time.localtime()[:8]
		if not self.button_state and tmp > (fps<<2):
			if self.date_was_shown:
				display.clear()
				self.date_was_shown = False
			if self.columns == 32:
				text = '  {:02d}:{:02d}  '.format(hour, minute)
				if (int(time.ticks_ms() // 100.0) % 10) < 4:
					text = text.replace(':', ' ')
				display.render_text(PixelFont, text, 2, y_off, intensity)
			else:
				text = '{:02d}'.format(hour)
				display.render_text(PixelFont, text, 4, y_off, intensity)
				text = '{:02d}'.format(minute)
				display.render_text(PixelFont, text, 4, y_off+8, intensity)
		else:
			if self.columns == 32:
				text = '{:02d}.{:02d}.{:02d}'.format(day, month, year % 100)
				display.render_text(PixelFont, text, 2, y_off, intensity)
			else:
				text = '{:02d}{:02d}'.format(day, month)
				display.render_text(PixelFont, text, 0, y_off, intensity)
				display.put_pixel(7, y_off+PixelFont.height, intensity, intensity, intensity)
				text = '{:04d}'.format(year)
				display.render_text(PixelFont, text, 0, y_off+8, intensity)
			self.date_was_shown = True

		x_off = 2 if self.columns == 32 else 1
		lower_intensity = intensity // 3
		for i in range(7):
			color = intensity if i == weekday else lower_intensity
			b = (color << 1) // 7
			display.put_pixel(x_off, 7, color, color, b)
			if self.columns == 32:
				display.put_pixel(x_off+1, 7, color, color, b)
				display.put_pixel(x_off+2, 7, color, color, b)
				x_off += 4
			else:
				x_off += 2

		display.render()
		if self.button_state == 2:
			self.button_state = 0

		# Signal that we want to be continued to be rendered
		return True
