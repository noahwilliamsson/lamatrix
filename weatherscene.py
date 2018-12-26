# Render the current weather forecast from SMHI.se
#
import time
import gc
try:
	import urequests as requests
except ImportError:
	import requests

# Local imports
from pixelfont import PixelFont
from icon import Icon

# Based on demoscene.py
class WeatherScene:
	"""
	This module displays a weather forecast from SMHI (Sweden)
	"""

	dir_prefix = 'weather/'

	def __init__(self, display, config):
		"""
		Initialize the module.
		`display` is saved as an instance variable because it is needed to
		update the display via self.display.put_pixel() and .render()
		"""
		self.display = display
		self.icon = None
		self.debug = False
		self.intensity = 16
		self.lat = 59.3293
		self.lon = 18.0686
		self.api_url = 'https://opendata-download-metfcst.smhi.se'
		self.headers = {
			'User-Agent':'weatherscene.py/1.0 (+https://github.com/noahwilliamsson/lamatrix)',
			'Accept-Encoding': 'identity',
		}
		self.temperature = 0
		self.wind_speed = 0
		self.last_refreshed_at = 0
		# http://opendata.smhi.se/apidocs/metfcst/parameters.html#parameter-wsymb
		self.symbol = None
		self.symbol_to_icon = [
			None,
			['moon-stars.bin', 'sunny.bin'],              # clear sky
			['moon-stars.bin', 'sunny-with-clouds.bin'],  # nearly clear sky
			'cloud-partly.bin', # variable cloudiness
			'sunny-with-clouds.bin', # halfclear sky
			'cloudy.bin',       # cloudy sky
			'cloudy.bin',       # overcast
			'fog.bin',          # fog
			'rain.bin',         # light rain showers
			'rain.bin',         # medium rain showers
			'rain.bin',         # heavy rain showers
			'rain.bin',         # thunderstorm
			'rain-snow.bin',    # light sleet showers
			'rain-snow.bin',    # medium sleet showers
			'rain-snow.bin',    # heavy sleet showers
			'rain-snow.bin',    # light snow showers
			'rain-snow.bin',    # medium snow showers
			'rain-snow.bin',    # heavy snow showers
			'rain.bin',         # light rain
			'rain.bin',         # medium rain
			'rain.bin',         # heavy rain
			'thunderstorm.bin', # thunder
			'rain-snowy.bin',   # light sleet
			'rain-snowy.bin',   # medium sleet
			'rain-snowy.bin',   # heavy sleet
			'snow-house.bin',   # light snowfall
			'snow-house.bin',   # medium snowfall
			'snow-house.bin',   # heavy snowfall
		]
		self.num_frames = 1
		self.remaining_frames = 1
		self.next_frame_at = 0
		if not config:
			return
		if 'debug' in config:
			self.debug = config['debug']
		if 'intensity' in config:
			self.intensity = int(round(config['intensity']*255))
		if 'lat' in config:
			self.lat = config['lat']
		if 'lon' in config:
			self.lon = config['lon']


	def reset(self):
		"""
		This method is called before transitioning to this scene.
		Use it to (re-)initialize any state necessary for your scene.
		"""
		self.next_frame_at = 0
		self.reset_icon()
		t = time.time()
		if t < self.last_refreshed_at + 1800:
			return

		# fetch a new forecast from SMHI
		url = '{}/api/category/pmp3g/version/2/geotype/point/lon/{}/lat/{}/data.json'.format(self.api_url, self.lon, self.lat)
		print('WeatherScene: reset called, requesting weather forecast from: {}'.format(url))

		r = requests.get(url, headers=self.headers, stream=True)
		if r.status_code != 200:
			print('WeatherScene: failed to request {}: status {}'.format(url, r.status_code))
			return

		print('WeatherScene: parsing weather forecast')
		next_hour = int(time.time())
		next_hour = next_hour - next_hour%3600 + 3600
		expected_timestamp = '{:04d}-{:02d}-{:02d}T{:02d}'.format(*time.gmtime(next_hour))
		temp, ws, symb = self.get_forecast(r.raw, expected_timestamp)
		# Close socket and free up RAM
		r.close()
		r = None
		gc.collect()

		if temp == None:
			print('WeatherScene: failed to find forecast for timestamp prefix: {}'.format(expected_timestamp))
			return
		self.temperature = float(temp.decode())
		self.wind_speed = float(ws.decode())
		self.symbol = int(symb.decode())
		self.last_refreshed_at = t

		filename = self.symbol_to_icon[self.symbol]
		if not filename:
			return

		if type(filename) == list:
			lt = time.localtime(next_hour)
			if lt[3] < 7 or lt[3] > 21:
				# Assume night icon
				filename = filename[0]
			else:
				filename = filename[1]
		if self.icon:
			# MicroPython does not support destructors so we need to manually
			# close the file we have opened
			self.icon.close()  # Close icon file
		self.icon = Icon(self.dir_prefix + filename)
		self.icon.set_intensity(self.intensity)
		self.reset_icon()

	def input(self, button_state):
		"""
		Handle button inputs
		"""
		return 0  # signal that we did not handle the input

	def set_intensity(self, value=None):
		if value is not None:
			self.intensity -= 1
			if not self.intensity:
				self.intensity = 16
			if self.icon:
				self.icon.set_intensity(self.intensity)
		return self.intensity

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
		# Calculate next frame number
		self.next_frame_at = frame + int(fps * self.icon.frame_length()/1000)
		# Render frame
		display = self.display
		intensity = self.intensity
		self.icon.blit(display, 0 if display.columns == 32 else 4, 0)

		# Render text
		if self.remaining_frames >= n:
			text = '{:.2g}\'c'.format(self.temperature)
		else:
			text = '{:.2g}m/s'.format(self.wind_speed)
			if display.columns <= 16:
				text = '{:.1g}m/s'.format(self.wind_speed)
		display.render_text(PixelFont, text, 9 if display.columns == 32 else 0, 1 if display.columns == 32 else 10, intensity)

		display.render()
		if self.remaining_frames == 0:
			return False
		return True

	def reset_icon(self):
		if not self.icon:
			return
		self.icon.reset()
		self.num_frames = self.icon.num_frames
		self.remaining_frames = self.num_frames*2
		t_icon = self.icon.length_total()
		# Ensure a minimum display time
		for i in range(1,6):
			if t_icon*i >= 4000:
				break
			self.remaining_frames += self.num_frames

	def get_forecast(self, f, validTime):
		"""
		Extract temperature, windspeed, weather symbol from JSON response
		"""
		timeStr = None
		tempStr = None
		wsStr = None
		symbStr = None
		while True:
			v = f.read(1)
			if v != b'"':
				continue
			s = self.next_string(f)
			if not timeStr:
				if not s.startswith(b'validTime'):
					continue
				timeStr = self.next_string(f, 2)
				if not timeStr.startswith(validTime):
					timeStr = None
					continue
			elif not tempStr and s == b't':
				tempStr = self.next_array_entry(f)
			elif not wsStr and s == b'ws':
				wsStr = self.next_array_entry(f)
			elif not symbStr and s == b'Wsymb2':
				symbStr = self.next_array_entry(f)
			elif timeStr and tempStr and wsStr and symbStr:
				break
		return (tempStr, wsStr, symbStr)

	def next_string(self, f, start_at = 0):
		"""
		Extract string value from JSON
		"""
		if start_at:
			f.read(start_at)
		stash = bytearray()
		while True:
			c = f.read(1)
			if c == b'"':
				break
			stash.append(c[0])
		return bytes(stash)

	def next_array_entry(self, f):
		"""
		Extract first array entry from JSON
		"""
		in_array = False
		stash = bytearray()
		while True:
			c = f.read(1)
			if not in_array:
				if c != b'[':
					continue
				in_array = True
				continue
			if c == b']' or c == b' ' or c == b',':
				break
			stash.append(c[0])
		return bytes(stash)
