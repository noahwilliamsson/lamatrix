# HAL for mainline MicroPython running on ESP8266
from neopixel import NeoPixel
from machine import Pin
from ntptime import settime
class uPyHAL:
	def __init__(self, config):
		self.num_pixels = 64
		self.np = NeoPixel(Pin(13), self.num_pixels)
		self.enable_auto_time = False
		# https://github.com/micropython/micropython/issues/2130
		#utime.timezone(config['tzOffsetSeconds'])
	def init_display(self, num_pixels=64):
		self.clear_display()
	def clear_display(self):
		for i in range(self.num_pixels):
			self.np[i] = (0,0,0)
			self.np.write()
	def update_display(self, num_modified_pixels):
		if not num_modified_pixels:
			return
		self.np.write()
	def put_pixel(self, addr, r, g, b):
		self.np[addr % self.num_pixels] = (r,g,b)
	def reset(self):
		self.clear_display()
	def process_input(self):
		#TODO: implement
		return 0
	def set_rtc(self, t):
		settime()
	def set_auto_time(self, enable=True):
		self.enable_auto_time = enable
	def suspend_host(self, restart_timeout_seconds):
		if restart_timeout_seconds < 15:
			return
