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
from machine import Pin, RTC, UART
import utime
import os
import sys
import pycom
import gc

class PycomHAL:
	def __init__(self, config):
		self.chain = None   # will be initialized in reset()
		self.num_pixels = 256
		self.reset()
		self.enable_auto_time = True
		# A Raspberry Pi will reboot/wake up if this pin is set low
		# https://docs.pycom.io/firmwareapi/pycom/machine/pin.html#pinholdhold
		self.suspend_host_pin = Pin('P8', Pin.OUT, Pin.PULL_UP)
		self.suspend_host_pin.hold(True)
		# Handle button input
		self.left_button = Pin('P9', Pin.IN, Pin.PULL_UP)
		self.left_button.callback(Pin.IRQ_FALLING|Pin.IRQ_RISING, handler=lambda arg: self.button_irq(arg))
		self.right_button = Pin('P10', Pin.IN, Pin.PULL_UP)
		self.right_button.callback(Pin.IRQ_FALLING|Pin.IRQ_RISING, handler=lambda arg: self.button_irq(arg))
		print('PycomHAL: left button {}, right button {}'.format(self.left_button.value(), self.right_button.value()))
		self.button_state = 0
		self.button_down_t = 0
		# Setup RTC
		self.rtc = None
		utime.timezone(config['tzOffsetSeconds'])
		pycom.heartbeat(False)
		# Free resources
		if self.left_button.value() and self.right_button.value():
			self.disable_stuff()

		# For the serial bridge implementation
		self.uart = None
		self.console = None
		gc.collect()
		self.rxbuf = bytearray(256)
		self.reconfigure_uarts(config)
		# Needed for maintaining the serial protocol state
		self.reboot_at = 0
		self.state = 0
		self.acc = 0
		self.color = 0
		gc.collect()

	def disable_stuff(self):
		from network import Bluetooth, Server
		bluetooth = Bluetooth()
		bluetooth.deinit()
		# Disable FTP server unless button is pressed during startup
		server = Server()
		server.deinit()
		print('PycomHAL: FTP server disabled (hold any button during startup to enable)')

	def reconfigure_uarts(self, config):
		"""
		Reconfigure UARTs to make
		- UART 0 become the one we can be controlled by via USB serial
		- UART 1 the console (print output and REPL)
		"""
		self.uart = UART(0, config['baudrate'], pins=('P1', 'P0', 'P20', 'P19'))  # TX/RX/RTS/CTS on ExpBoard2
		self.console = UART(1, 115200)
		if not config or not 'remapConsole' in config or config['remapConsole']:
			print('HAL: Disabling REPL on UART0 and switching to serial protocol')
			os.dupterm(self.console)
			print('HAL: Enabled REPL on UART1')

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
		shift = 0 if pin == self.left_button else 4
		if t > 1500:
			self.button_state |= 1<<(shift+2)
		elif t > 500:
			self.button_state |= 1<<(shift+1)
		elif t > 80:
			self.button_state |= 1<<(shift+0)
		self.button_down_t = 0

	# Implement the serial protocol understood by ArduinoSerialHAL
	# This function should be similar to the Arduino project's loop()
	def process_input(self):
		"""
		Process control messages coming from the host as well as any
		button presses captured.  Return button presses as input to
		the caller (the main game loop).
		Also takes care of waking up the host computer if the timer expired.
		"""
		# Wake up the host computer if necessary
		if self.reboot_at:
			if utime.time() > self.reboot_at:
				self.reboot_at = 0
				# Trigger wakeup
				print('HAL: Waking up host computer')
				self.suspend_host_pin.hold(False)
				self.suspend_host_pin(0)
				self.suspend_host_pin(1)
				self.suspend_host_pin.hold(True)

		# Process button input
		button_state = self.button_state
		if button_state:
			try:
				if button_state & 1:
					# Notify the host about the button press in a similar manner
					# to what ArduinoSer2FastLED does
					self.uart.write(bytearray('LEFTB_SHRT_PRESS\n'))
				elif button_state & 2:
					self.uart.write(bytearray('LEFTB_LONG_PRESS\n'))
				elif button_state & 4:
					self.uart.write(bytearray('LEFTB_HOLD_PRESS\n'))
				elif button_state & 16:
					self.uart.write(bytearray('RGHTB_SHRT_PRESS\n'))
				elif button_state & 32:
					self.uart.write(bytearray('RGHTB_LONG_PRESS\n'))
				elif button_state & 64:
					self.uart.write(bytearray('RGHTB_HOLD_PRESS\n'))
			except OSError as e:
				print('HAL: UART write failed: {}'.format(e.args[0]))
			self.button_state = 0

		avail = self.uart.any()
		if not avail:
			# No incoming data from the host, return the button state to the
			# caller (game loop) so it can process it if self.enable_auto_time
			# is True
			return button_state

		if avail > 256:
			# Currently shipping releases have a 512 byte buffer
			print('HAL: More than 256 bytes available: {}'.format(avail))

		self.uart.readinto(self.rxbuf)
		for val in self.rxbuf:
			if self.state == 0:
				if not val:
					# Host is trying to resynchronize
					self.uart.write(bytearray('RESET\n'))
					print('HAL: Reset sequence from host detected or out-of-sync')
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
				self.clear_display()
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
		return button_state

	def reset(self):
		print('HAL: Reset called')
		self.chain = WS2812(ledNumber=self.num_pixels)
		gc.collect()

	def init_display(self, num_pixels=256):
		print('HAL: Initializing display with {} pixels'.format(num_pixels))
		self.num_pixels = num_pixels
		self.chain.clear()
		self.chain.send_buf()

	def clear_display(self):
		"""
		Turn off all pixels
		"""
		self.chain.clear()
		self.update_display(self.num_pixels)

	def update_display(self, num_modified_pixels):
		if not num_modified_pixels:
			return
		self.chain.send_buf()

	def put_pixel(self, addr, r, g, b):
		"""
		Update pixel in buffer
		"""
		self.chain.put_pixel(addr % self.num_pixels, r, g, b)

	def set_rtc(self, scene):
		# Resynchronize RTC
		self.rtc = RTC()
		self.rtc.ntp_sync('ntps1-1.eecsit.tu-berlin.de')
		print('HAL: Waiting for NTP sync')
		if type(scene) != int:
			# Kludge: render RTC sync progress
			frame = 0
			while not self.rtc.synced():
				scene.render(frame, 0, 0)
				frame += 1
		print('HAL: RTC synched')

	def set_auto_time(self, enable=True):
		"""
		Enable rendering of current time without involvment from host computer
		"""
		self.enable_auto_time = enable
		gc.collect()

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
