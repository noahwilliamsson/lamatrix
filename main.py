#!/usr/bin/env python
#
# This is a project to drive a 32x8 or 16x16 LED matrix based on the popular
# WS2812 RGB LEDs using a microcontroller running MicroPython (preferrably
# one with 4MB RAM although modules with 1MB also work).
#
#   -- noah@hack.se, 2018
#
import sys
import time
import gc
from math import ceil
from ledmatrix import LedMatrix
# This is to make sure we have a large contiguous block of RAM on devices with
# 520kB RAM after all modules and modules have been compiled and instantiated.
#
# In the weather scene, the ussl module needs a large chunk of around 1850
# bytes, and without the dummy allocation below the heap will be too
# fragmented after all the initial processing to find such a large chunk.
large_temp_chunk = bytearray(3400)

pycom_board = False
esp8266_board = False
if hasattr(sys,'implementation') and sys.implementation.name == 'micropython':
	import ujson as json
	import machine
	from network import WLAN
	from os import uname
	tmp = uname()
	if tmp.sysname == 'esp8266':
		esp8266_board = True
		from upyhal import uPyHAL as HAL
	else:
		pycom_board = True
		from pycomhal import PycomHAL as HAL
	tmp = None
	del uname
else:
	import json
	import os
	import signal
	# Kludge to allow this project to be used with a Raspberry Pi instead of
	# an MCU: see https://github.com/noahwilliamsson/lamatrix/issues/1
	try:
		# If the rpi_ws281x Python module is available, then use that...
		from raspberrypihal import RaspberryPiHAL as HAL
	except:
		# ...else assume that there's an MCU (driving the display) connected
		# to a serial port
		from arduinoserialhal import ArduinoSerialHAL as HAL

gc.collect()
from renderloop import RenderLoop


def sigint_handler(sig, frame):
	"""
	Clear display when the program is terminated by Ctrl-C or SIGTERM
	"""
	global driver
	driver.clear_display()
	driver.set_auto_time(True)
	sys.exit(0)


if __name__ == '__main__':
	f = open('config.json')
	config = json.loads(f.read())
	f.close()
	del json

	# Initialize HAL
	driver = HAL(config)
	if not esp8266_board and not pycom_board:
		# We're running on the host computer here
		ports = [
			'/dev/tty.usbmodem575711',      # Teensy 3.x on macOS
			'/dev/tty.usbserial-DQ008J7R',  # Pycom device on macOS
			'/dev/ttyUSB0',                 # Linux
			'/dev/ttyACM0',                 # Linux
		]
		for port in ports:
			if os.path.exists(port):
				config['port'] = port
				break
		# Disable automatic rendering of time
		driver.set_auto_time(False)
		# Trap Ctrl-C and service termination
		signal.signal(signal.SIGINT, sigint_handler)
		signal.signal(signal.SIGTERM, sigint_handler)

	# Initialize led matrix framebuffer on top of HAL
	display = LedMatrix(driver, config['LedMatrix'])
	driver.clear_display()

	if pycom_board:
		# We're running under MCU here
		from bootscene import BootScene
		scene = BootScene(display, config['Boot'])
		wlan = WLAN(mode=WLAN.STA)
		if not wlan.isconnected():
			print('WLAN: Scanning for networks')
			scene.render(0,0,0)
			default_ssid, default_auth = wlan.ssid(), wlan.auth()
			candidates = wlan.scan()
			for conf in config['networks']:
				nets = [candidate for candidate in candidates if candidate.ssid == conf['ssid']]
				if not nets:
					continue
				print('WLAN: Connecting to known network: {}'.format(nets[0].ssid))
				wlan.connect(nets[0].ssid, auth=(nets[0].sec, conf['password']))
				for i in range(1,40):
					scene.render(i, 0, 0)
					time.sleep(0.2)
					if wlan.isconnected():
						break
				if wlan.isconnected():
					break
		scene.render(0, 0, 0)
		if not wlan.isconnected():
			# TODO: This will only use SSID/auth settings from NVRAM during cold boots
			print('WLAN: No known networks, enabling AP with ssid={}, pwd={}'.format(default_ssid, default_auth[1]))
			wlan.init(mode=WLAN.AP, ssid=default_ssid, auth=default_auth, channel=6)
		else:
			display.clear()
			print('WLAN: Connected with IP: {}'.format(wlan.ifconfig()[0]))
			# Initialize RTC now that we're connected
			driver.set_rtc(scene)
			scene.render(0,0,0)
		scene = None
		del BootScene
	elif esp8266_board:
		pass


	# This is where it all begins
	r = RenderLoop(display, config)

	if 'Clock' in config:
		from clockscene import ClockScene
		scene = ClockScene(display, config['Clock'])
		r.add_scene(scene)
		gc.collect()

	if 'Demo' in config:
		from demoscene import DemoScene
		scene = DemoScene(display, config['Demo'])
		r.add_scene(scene)
		gc.collect()

	if 'Weather' in config:
		from weatherscene import WeatherScene
		scene = WeatherScene(display, config['Weather'])
		r.add_scene(scene)
		gc.collect()

	if 'Fire' in config:
		from firescene import FireScene
		scene = FireScene(display, config['Fire'])
		r.add_scene(scene)
		gc.collect()

	if 'Animation' in config:
		from animationscene import AnimationScene
		scene = AnimationScene(display, config['Animation'])
		r.add_scene(scene)
		gc.collect()

	# Now that we're all setup, release the large chunk
	large_temp_chunk = None

	# Render scenes forever
	while True:
		# Process input
		button_state = 0
		if pycom_board:
			# When running under MicroPython on the MCU we need to deal with
			# any input coming from the host over the serial link
			while True:
				button_state = driver.process_input()
				if driver.enable_auto_time:
					# If the host disconnected we'll hand over control to the
					# game loop which will take care of updating the display
					break
		else:
			# When running under regular Python on the host computer we need
			# to pick up any button presses sent over the serial link from
			# the Arduino firmware
			n = 0
			while True:
				# Drain output from MCU and detect button presses
				line = driver.process_input()
				if not line:
					break
				event = line.strip()
				if event == 'LEFTB_SHRT_PRESS':
					button_state = 1
				elif event == 'LEFTB_LONG_PRESS':
					button_state = 2
				else:
					print('MCU: {}'.format(event))
		r.next_frame(button_state)
