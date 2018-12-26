#!/usr/bin/env python
#
# This code is running on the host and implements the serial protocol
# used to control the display connected to the MCU.
#
# On the MCU side, the serial protocol is either implemented under Arduino
# or under MicroPython.
#
import serial
import time

class ArduinoSerialHAL:
	"""
	ArduinoSerialHAL is handles the serial protocol (API) used to control
	the display connected to the MCU.
	"""

	def __init__(self, config):
		self.port = config['port']
		self.baudrate = config['baudrate']
		self.tz_adjust = config['tzOffsetSeconds']
		self.ser = None  # initialized in reset()
		self.reset()

	def process_input(self):
		"""
		Process data coming from the MCU over the serial link, such as any
		captured button presses by the firmware or log messages, and return
		it as input data to the caller (the main game loop)
		"""
		if not self.ser.in_waiting:
			return None
		line = self.ser.readline()
		return line

	def reset(self):
		"""
		(Re-)open serial ports and resynchronize the protocol
		"""
		if self.ser:
			print('SerialProtocol: closing serial link')
			self.ser.close()
		print('SerialProtocol: opening port {} @ {} baud'.format(self.port, self.baudrate))
		self.ser = serial.Serial(self.port, baudrate=self.baudrate, rtscts=True, timeout=0.1, write_timeout=0.5)
		self.resynchronize_protocol()
		self.set_rtc(int(time.time()) + self.tz_adjust)

	def resynchronize_protocol(self):
		"""
		Resynchronize the protocol by writing a string of zeroes.
		"""
		data = bytearray(10)
		self.ser.write(data)

	def safe_write(self, data):
		"""
		Write data to the serial link and attempt to handle write timeouts
		"""
		try:
			self.ser.write(data)
			return
		except serial.SerialTimeoutException:
			print('SerialProtocol: write timeout, attempting reset..')
			print('WARN: Serial write timed out, attempting reset')
			self.reset()
			print('SerialProtocol: retrying send of {} bytes'.format(len(data)))
			self.ser.write(data)

	def init_display(self, num_pixels=256):
		# Setup FastLED library
		data = bytearray(3)
		data[0] = ord('i')
		data[1] = num_pixels & 0xff
		data[2] = (num_pixels >> 8) & 0xff
		self.safe_write(data)

	def clear_display(self):
		data = bytearray(2)
		data[0] = ord('c')
		self.safe_write(data)

	def update_display(self, num_modified_pixels=None):
		data = bytearray(2)
		data[0] = ord('s')
		self.safe_write(data)

	def put_pixel(self, addr, r, g, b):
		data = bytearray(6)
		data[0] = ord('l')
		data[1] = (addr >> 0) & 0xff
		data[2] = (addr >> 8) & 0xff
		data[3] = r
		data[4] = g
		data[5] = b
		self.safe_write(data)

	def set_rtc(self, t):
		# Resynchronize RTC
		data = bytearray(5)
		data[0] = ord('@')
		t = int(t)
		data[1] = (t >> 0) & 0xff
		data[2] = (t >> 8) & 0xff
		data[3] = (t >> 16) & 0xff
		data[4] = (t >> 24) & 0xff
		self.safe_write(data)

	def set_auto_time(self, enable=True):
		# Enable or disable automatic rendering of current time
		data = bytearray(2)
		data[0] = ord('t')
		data[1] = int(enable)
		self.safe_write(data)

	def suspend_host(self, restart_timeout_seconds):
		data = bytearray(3)
		data[0] = ord('S')
		data[1] = (restart_timeout_seconds >> 0) & 0xff
		data[2] = (restart_timeout_seconds >> 8) & 0xff
		self.safe_write(data)

if __name__ == '__main__':
	import os
	import time
	port = '/dev/tty.usbmodem575711'
	if not os.path.exists(port):
		port = '/dev/ttyACM0'

	p = SerialProtocol(port, 115200)
	p.init_display(256)
	p.clear_display()
	p.put_pixel(0, 8, 0, 0)
	p.put_pixel(8, 0, 8, 0)
	p.put_pixel(16, 0, 0, 8)
	p.update_display()
	time.sleep(1)
	p.clear_display()
