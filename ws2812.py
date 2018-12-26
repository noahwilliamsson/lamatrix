# -*- coding: utf-8 -*-
"""This code is borrowed from https://github.com/JanBednarik/micropython-ws2812

It has been modified to work on, and has been tested upon, the Pycom WiPy 2.0 board.

It uses SPI MOSI (Master-out Slave-in) which is P11 or (on the pymakr board) G22.
See: https://docs.pycom.io/chapter/datasheets/downloads/wipy2-pinout.pdf

Modifications include:
* Changing buf_bytes to 0b representation for clearer view of what's happening internally
* Switch to machine.SPI instead of pyb.SPIfor Pycom WiPy 2.0 board
* Adding disable_irq and enable_irq to prevent interrupts firing mid-transaction and causing a premature reset
"""

import gc
from machine import SPI
from machine import disable_irq
from machine import enable_irq


class WS2812:
	"""
	Driver for WS2812 RGB LEDs. May be used for controlling single LED or chain
	of LEDs.
	Example of use:
		chain = WS2812(spi_bus=1, led_count=4)
		data = [
			(255, 0, 0),	# red
			(0, 255, 0),	# green
			(0, 0, 255),	# blue
			(85, 85, 85),   # white
		]
		chain.show(data)
	Version: 1.0
	"""
	buf_bytes = (0b000010001, 0b00010011, 0b00110001, 0b00110011)

	def __init__(self, spi_bus=0, ledNumber=1, intensity=1):
		"""
		Params:
		* spi_bus = SPI bus ID (1 or 2)
		* led_count = count of LEDs
		* intensity = light intensity (float up to 1)
		"""
		self.led_count = ledNumber
		self.intensity = intensity

		# prepare SPI data buffer (4 bytes for each color)
		self.buf_length = self.led_count * 3 * 4
		self.buf = bytearray(self.buf_length)

		# SPI init
		self.spi = SPI(spi_bus, SPI.MASTER, baudrate=3200000, polarity=0, phase=1)

		# turn LEDs off
		self.send_buf()

	def send_buf(self):
		"""
		Send buffer over SPI.
		"""
		disable_irq()
		self.spi.write(self.buf)
		enable_irq()

	# NOTE: show(), update_buf() and fill_buf() were replaced
	#       with these to reduce memory usage in pycomhal.py
	def clear(self):
		# turn off the rest of the LEDs
		buf = self.buf
		off = self.buf_bytes[0]
		for index in range(self.buf_length):
			buf[index] = off
			index += 1

	def put_pixel(self, addr, red, green, blue):
		buf = self.buf
		buf_bytes = self.buf_bytes
		mask = 0x03
		index = addr * 12
		buf[index] = buf_bytes[green >> 6 & mask]
		buf[index+1] = buf_bytes[green >> 4 & mask]
		buf[index+2] = buf_bytes[green >> 2 & mask]
		buf[index+3] = buf_bytes[green & mask]

		buf[index+4] = buf_bytes[red >> 6 & mask]
		buf[index+5] = buf_bytes[red >> 4 & mask]
		buf[index+6] = buf_bytes[red >> 2 & mask]
		buf[index+7] = buf_bytes[red & mask]

		buf[index+8] = buf_bytes[blue >> 6 & mask]
		buf[index+9] = buf_bytes[blue >> 4 & mask]
		buf[index+10] = buf_bytes[blue >> 2 & mask]
		buf[index+11] = buf_bytes[blue & mask]
