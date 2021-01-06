# HAL for Raspberry Pi with https://github.com/rpi-ws281x/rpi-ws281x-python
# See https://github.com/jgarff/rpi_ws281x for more details on this library.
#
# The below code assumes the LED strip is connected to GPIO 18 (PCM CLK)
# (see https://pinout.xyz) and that you've installed the rpi_ws281x library.
#
# For Python 2.x:
#
#   sudo apt install -y python-pip; sudo pip install rpi_ws281x
#
# For Python 3.x:
#
#   sudo apt install -y python3-pip; sudo pip3 install rpi_ws281x
#
#
from rpi_ws281x import PixelStrip, Color

# LED strip configuration:
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

class RaspberryPiHAL:
	def __init__(self, config):
		self.num_pixels = config['LedMatrix']['columns'] * config['LedMatrix']['stride']
		self.strip = PixelStrip(self.num_pixels, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
		self.strip.begin()
	def init_display(self, num_pixels=64):
		self.clear_display()
	def clear_display(self):
		c = Color(0, 0, 0)
		for i in range(self.num_pixels):
			self.strip.setPixelColor(i, c)
		self.strip.show()
	def update_display(self, num_modified_pixels):
		if not num_modified_pixels:
			return
		self.strip.show()
	def put_pixel(self, addr, r, g, b):
		self.strip.setPixelColor(addr % self.num_pixels, Color(r, g, b))
	def reset(self):
		self.clear_display()
	def process_input(self):
		#TODO: implement
		return 0
	def set_rtc(self, t):
		#Not relevant
		pass
	def set_auto_time(self, enable=True):
		#Not relevant
		pass
	def suspend_host(self, restart_timeout_seconds):
		#Not relevant
		pass
