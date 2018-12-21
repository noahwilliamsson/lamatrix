#!/usr/bin/env python
#
# This file is running on the MCU and implements the following features:
# - the serial protocol used to control the MCU from a host computer
# - low-level LED matrix routines (initialization, put pixel, ..)
# - configuration of the real-time clock
# - shutdown/power-up of the host computer (via GPIO)
#
# This file is similar to the Arduino C version running on Teensy.
#
# From https://raw.githubusercontent.com/Gadgetoid/wipy-WS2812/master/ws2812alt.py
# ..via: https://forum.pycom.io/topic/2214/driving-ws2812-neopixel-led-strip/3
from ws2812 import WS2812
#from rmt import WS2812
from machine import Pin, RTC, UART, idle
import utime
import os
import sys
import pycom
import gc

# Local imports
from clockscene import ClockScene
from weatherscene import WeatherScene

class PycomHAL:
	def __init__(self, config):
		self.chain = None   # will be initialized in reset()
		self.num_pixels = 256
		self.pixels = []
		self.reset()
		self.enable_auto_time = True
		self.frame = 0
		# TODO: Fix these
		self.scene = 0
		self.clock = None
		self.weather = None
		self.config = config
		# A Raspberry Pi will reboot/wake up if this pin is set low
		# https://docs.pycom.io/firmwareapi/pycom/machine/pin.html#pinholdhold
		self.suspend_host_pin = Pin('P8', Pin.OUT, Pin.PULL_UP)
		self.suspend_host_pin.hold(True)
		# Handle button input
		self.button_pin = Pin('P12', Pin.IN, Pin.PULL_UP)
		self.button_pin.callback(Pin.IRQ_FALLING|Pin.IRQ_RISING, handler=lambda arg: self.button_irq(arg))
		self.button_state = 0
		self.button_down_t = 0
		# Setup RTC
		self.rtc = None
		self.set_rtc(0)
		utime.timezone(config['tzOffsetSeconds'])
		pycom.heartbeat(False)
		gc.collect()

		# For the serial bridge implementation
		self.uart = None  # will be initialized in serial_loop()
		self.reboot_at = 0
		self.state = 0
		self.acc = 0
		self.color = 0

	def button_irq(self, pin):
		"""
		Interrrupt handler for button input pin
		"""
		level = pin.value()
		if not level:
			self.button_down_t = utime.ticks_ms()
			return
		if not self.button_down_t:
			return
		t = utime.ticks_ms() - self.button_down_t
		if t > 500:
			self.button_state = 2
		elif t > 80:
			self.button_state = 1
		self.button_down_t = 0

	# Implement the serial protocol understood by ArduinoSerialHAL
	# This function should be similar to the Arduino project's loop()
	def serial_loop(self, display):
		if self.reboot_at:
			if utime.time() > self.reboot_at:
				self.reboot_at = 0
				# Trigger wakeup
				print('HAL: Waking up host computer')
				self.suspend_host_pin.hold(False)
				self.suspend_host_pin(0)
				self.suspend_host_pin(1)
				self.suspend_host_pin.hold(True)

		if not self.uart:
			print('HAL: Disabling REPL on UART0 and switching to serial protocol')
			idle()
			os.dupterm(None)
			self.uart = UART(0, 115200*8, pins=('P1', 'P0', 'P20', 'P19'))  # TX/RX/RTS/CTS on ExpBoard2
			self.console = UART(1, 115200)
			os.dupterm(self.console)
			idle()
			print('HAL: Enabled REPL on UART1')

		button_state = self.button_state
		if button_state:
			if button_state == 1:
				print('BUTTON_SHRT_PRESS')
			elif button_state == 2:
				print('BUTTON_LONG_PRESS')
			self.button_state = 0

		if self.enable_auto_time:
			# TODO: Unify with main.py::RenderLoop
			self.frame += 1
			if not self.clock:
				print('HAL: Initiating clock scene')
				self.clock = ClockScene(display, self.config['ClockScene'])
			if not self.weather:
				self.weather = WeatherScene(display, self.config['WeatherScene'])
				self.weather.reset()

			if button_state == 1:
				self.clock.input(0, button_state)
			elif button_state == 2:
				self.scene ^= 1
				self.clear_display()

			if self.scene == 0:
				self.clock.render(self.frame, 0, 5)
			else:
				self.weather.render(self.frame, 0, 5)

		avail = self.uart.any()
		if not avail:
			return
		if avail > 256:
			# Currently shipping releases have a 512 byte buffer
			print('HAL: More than 256 bytes available: {}'.format(avail))

		data = self.uart.readall()
		for val in data:
			if self.state == 0:
				# reset
				self.state = val
			elif self.state >= ord('i') and self.state <= ord('i')+1:
				# init display
				tmp = self.state - ord('i')
				self.state += 1      # next state
				if tmp == 0:
					self.acc = val
				elif tmp == 1:
					self.acc += val << 8
					self.init_display(self.acc)
					self.state = 0   # reset state
			elif self.state == ord('c'):
				# clear display
				self.clear_display()
				self.state = 0       # reset state
			elif self.state == ord('s'):
				# show display
				self.update_display(self.num_pixels)
				self.state = 0       # reset state
			elif self.state >= ord('l') and self.state <= ord('l')+5:
				# put pixel
				tmp = self.state - ord('l')
				self.state += 1      # next state
				if tmp == 0:
					self.acc = val
				elif tmp == 1:
					self.acc += val << 8
				elif tmp == 2:
					self.color = val
				elif tmp == 3:
					self.color += val << 8
				elif tmp == 4:
					self.color += val << 16
					c = self.color
					self.put_pixel(self.acc, (c >> 0) & 0xff, (c >> 8) & 0xff, (c >> 16) & 0xff)
					self.state = 0   # reset state
			elif self.state >= ord('S') and self.state <= ord('S')+1:
				# suspend host
				tmp = self.state - ord('S')
				self.state += 1      # next state
				if tmp == 0:
					self.acc = val
				else:
					self.acc += val << 8
					self.reboot_at = int(utime.time()) + self.acc
					# TODO: flip pin to reboot host
					self.state = 0   # reset state
			elif self.state == ord('t'):
				# automatic rendering of current time
				if val == 10 or val == 13:
					self.set_auto_time(not self.enable_auto_time)
				else:
					self.set_auto_time(bool(val))
				print('HAL: Automatic rendering of time is now: {}'.format(self.enable_auto_time))
				self.state = 0       # reset state
			elif self.state >= ord('@') and self.state <= ord('@')+3:
				# update RTC
				tmp = self.state - ord('@')
				self.state += 1      # next state
				if tmp == 0:
					self.acc += val
				elif tmp == 1:
					self.acc += val << 8
				elif tmp == 2:
					self.acc += val << 16
				if tmp == 3:
					self.acc += val << 24
					self.set_rtc(self.acc)
					self.state = 0   # reset state
			else:
				print('HAL: Unhandled state: {}'.format(self.state))
				self.state = 0       # reset state

	def readline(self):
		"""
		No-op in this implementation
		"""
		return None

	def reset(self):
		print('HAL: Reset called')
		self.chain = WS2812(ledNumber=self.num_pixels, intensity=0.5)

	def init_display(self, num_pixels=256):
		print('HAL: Initializing display with {} pixels'.format(num_pixels))
		self.num_pixels = num_pixels
		self.pixels = [(0,0,0) for _ in range(self.num_pixels)]
		self.clear_display()

	def clear_display(self):
		for i in range(self.num_pixels):
			self.pixels[i] = (0,0,0)
		self.update_display(self.num_pixels)

	def update_display(self, num_modified_pixels):
		if not num_modified_pixels:
			return
		self.chain.show(self.pixels[:num_modified_pixels])
		gc.collect()

	def put_pixel(self, addr, r, g, b):
		self.pixels[addr % self.num_pixels] = (r,g,b)

	def set_rtc(self, t):
		# Resynchronize RTC
		self.rtc = RTC()
		self.rtc.ntp_sync('ntps1-1.eecsit.tu-berlin.de')
		print('HAL: Waiting for NTP sync')
		while not self.rtc.synced():
			idle()
		print('HAL: RTC synched')

	def set_auto_time(self, enable=True):
		"""
		Enable rendering of current time without involvment from host computer
		"""
		self.enable_auto_time = enable

	def suspend_host(self, restart_timeout_seconds):
		"""
		Suspend host computer and configure a future wakeup time
		"""
		if restart_timeout_seconds < 15:
			return
		self.reboot_at = utime.time() + restart_timeout_seconds
		# Trigger shutdown
		self.suspend_host_pin.hold(False)
		self.suspend_host_pin(0)
		self.suspend_host_pin(1)
		self.suspend_host_pin.hold(True)
		pass

if __name__ == '__main__':
	import os
	import time
	p = PycomHAL()
	p.init_display(256)
	p.clear_display()
	p.put_pixel(0, 8, 0, 0)
	p.put_pixel(8, 0, 8, 0)
	p.put_pixel(16, 0, 0, 8)
	p.update_display(p.num_pixels)
	time.sleep(1)
	p.clear_display()
