#!/usr/bin/env python
#
# Render the current weather forecast from SMHI.se
#
import os
import time
try:
	import ujson as json
	import urequests as requests
except ImportError:
	import json
	import requests

# Local imports
from pixelfont import PixelFont

# Based on demoscene.py
class WeatherScene:
	"""
	This module displays a weather forecast from SMHI (Sweden)
	"""

	def __init__(self, display, config):
		"""
		Initialize the module.
		`display` is saved as an instance variable because it is needed to
		update the display via self.display.put_pixel() and .render()
		"""
		self.display = display
		self.font = PixelFont()
		self.last_refreshed_at = 0
		self.api_url = 'https://opendata-download-metfcst.smhi.se'
		self.lat = 59.3293
		self.lon = 18.0686
		if config:
			if 'lat' in config:
				self.lat = config['lat']
			if 'lon' in config:
				self.lon = config['lon']

		self.headers = {
			'User-Agent':'weatherscene.py/1.0 (+https://github.com/noahwilliamsson/lamatrix)',
		}
		self.temperature = 0
		self.wind_speed = 0
		# http://opendata.smhi.se/apidocs/metfcst/parameters.html#parameter-wsymb
		self.symbol = None
		self.symbol_version = 1
		self.symbol_to_animation = [
			None,
			'weather/weather-moon-stars.json',   # clear sky
			'weather/weather-moon-stars.json',   # nearly clear sky
			'weather/weather-cloud-partly.json', # variable cloudiness
			'weather/weather-cloud-partly.json', # halfclear sky
			'weather/weather-cloudy.json',       # cloudy sky
			'weather/weather-cloudy.json',       # overcast
			'weather/weather-cloudy.json',       # fog
			'weather/weather-rain.json',         # rain showers
			'weather/weather-rain.json',         # thunderstorm
			'weather/weather-rain-snowy.json',   # light sleet
			'weather/weather-rain-snowy.json',   # snow showers
			'weather/weather-rain.json',         # rain
			'weather/weather-thunderstorm.json', # thunder
			'weather/weather-rain-snowy.json',   # sleet
			'weather/weather-snow-house.json',   # snowfall
		]
		self.frames = [[[]]]
		self.delays = [0]
		self.remaining_frames = 1
		self.next_frame_at = 0
		self.loops = 3

	def reset(self):
		"""
		This method is called before transitioning to this scene.
		Use it to (re-)initialize any state necessary for your scene.
		"""
		self.remaining_frames = len(self.frames)*self.loops
		self.next_frame_at = 0

		t = time.time()
		if t < self.last_refreshed_at + 1800:
			return

		# fetch a new forecast from SMHI
		print('WeatherScene: reset called, requesting weather forecast')
		url = '{}/api/category/pmp2g/version/2/geotype/point/lon/{}/lat/{}/data.json'.format(self.api_url, self.lon, self.lat)
		r = requests.get(url, headers=self.headers)
		if r.status_code != 200:
			print('WeatherScene: failed to request {}: status {}'.format(url, r.status_code))
			return
		print('WeatherScene: parsing weather forecast')

		forecast = None
		expected_timestamp = '{:04d}-{:02d}-{:02d}T{:02d}'.format(*time.gmtime())
		data = json.loads(r.text)
		for ts in data['timeSeries']:
			if ts['validTime'].startswith(expected_timestamp):
				forecast = ts
				break

		if not forecast:
			print('WeatherScene: failed to find forecast for UNIX timestamp {}'.format(this_hour))
			return
		self.last_refreshed_at = t

		n = 0
		for obj in forecast['parameters']:
			if obj['name'] == 't':
				self.temperature = obj['values'][0]
			elif obj['name'] == 'ws':
				self.wind_speed = obj['values'][0]
			elif obj['name'] == 'Wsymb':
				# http://opendata.smhi.se/apidocs/metfcst/parameters.html#parameter-wsymb
				self.symbol = obj['values'][0]
				self.symbol_version = 1
			elif obj['name'] == 'Wsymb2':
				# http://opendata.smhi.se/apidocs/metfcst/parameters.html#parameter-wsymb
				self.symbol = obj['values'][0]
				self.symbol_version = 2
			else:
				continue
			n += 1
		print('WeatherScene: updated {} parameters from forecast for {}'.format(n, forecast['validTime']))

		filename = self.symbol_to_animation[self.symbol]
		if not filename:
			return
		f = open(filename)
		obj = json.loads(f.read())
		f.close()
		obj = json.loads(obj['body'])
		self.delays = obj['delays']
		self.frames = obj['icons']
		self.num_frames = len(self.frames)
		self.remaining_frames = self.num_frames*4

	def input(self, button_id, button_state):
		print('WeatherScene: button {} pressed: {}'.format(button_id, button_state))
		return False  # signal that we did not handle the input

	def render(self, frame, dropped_frames, fps):
		"""
		Render the scene.
		This method is called by the render loop with the current frame number,
		the number of dropped frames since the previous invocation and the
		requested frames per second (FPS).
		"""

		if frame < self.next_frame_at:
			return True

		self.remaining_frames -= 1
		n = self.num_frames
		index = n - (self.remaining_frames % n) - 1
		# Calculate next frame
		self.next_frame_at = frame + int(fps * self.delays[index]/1000)
		# Render frame
		display = self.display
		data = self.frames[index]
		for y in range(len(data)):
			row = data[y]
			for x in range(len(data)):
				r = round(row[x][0] * 255)
				g = round(row[x][0] * 255)
				b = round(row[x][0] * 255)
				display.put_pixel(x, y, r, g, b)

		# Render text
		if self.remaining_frames >= n:
			text = '{:.2g}\'c'.format(self.temperature)
		else:
			text = '{:.2g}m/s'.format(self.wind_speed)
		self.render_text(text)

		display.render()
		if self.remaining_frames == 0:
			return False
		return True

	def render_text(self, text, x_off = 8+1, y_off = 1):
		"""
		Render text with the pixel font
		"""
		display = self.display
		f = self.font
		w = f.width
		h = f.height
		alphabet = f.alphabet
		font = f.data
		for i in range(len(text)):
			digit = text[i]
			if digit in '.-\'' or text[i-1] in '.':
				x_off -= 1
			data_offset = alphabet.find(digit)
			if data_offset < 0:
				data_offset = 0
			tmp = data_offset * w * h
			font_byte = tmp >> 3
			font_bit = tmp & 7
			for row in range(h):
				for col in range(w):
					c = 0
					if font[font_byte] & (1<<font_bit):
						c = 255
					font_bit += 1
					if font_bit == 8:
						font_byte += 1
						font_bit = 0
					display.put_pixel(x_off+col, y_off+row, c, c, c)
			x_off += w


if __name__ == '__main__':
	# Debug API
	scene = WeatherScene(None, None)
	scene.reset()
