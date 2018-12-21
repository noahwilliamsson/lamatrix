#!/usr/bin/env python
#
# This is a project to drive a 8x32 (or 8x8) LED matrix based on the
# popular WS2812 RGB LEDs using a microcontroller (e.g. a Teensy 3.x
# or a Pycom module with 4MB RAM) and optionally control them both
# using a more powerful host computer, such as a Raspberry Pi Zero W.
#
#   -- noah@hack.se, 2018
#
import sys
import time
from math import ceil
if hasattr(sys,'implementation') and sys.implementation.name == 'micropython':
	pycom_board = True
	import ujson as json
	import machine
	from network import WLAN
	# Local imports
	from pycomhal import PycomHAL
else:
	pycom_board = False
	# Emulate https://docs.pycom.io/firmwareapi/micropython/utime.html
	time.ticks_ms = lambda: int(time.time() * 1000)
	time.sleep_ms = lambda x: time.sleep(x/1000.0)
	import json
	import os
	import sys
	import signal
	# Local imports
	from arduinoserialhal import ArduinoSerialHAL

# Local imports
from ledmatrix import LedMatrix
from clockscene import ClockScene


class RenderLoop:
	def __init__(self, display = None, fps=10):
		self.display = display
		self.fps = fps
		self.t_next_frame = None
		self.prev_frame = 0
		self.frame = 1
		self.t_init = time.ticks_ms() / 1000.0
		self.debug = 1
		self.scenes = []
		self.scene_index = 0
		self.scene_switch_effect = 0
		self.reset_scene_switch_counter()

	def reset_scene_switch_counter(self):
		"""
		Reset counter used to automatically switch scenes.
		The counter is decreased in .next_frame()
		"""
		self.scene_switch_countdown = 45 * self.fps

	def add_scene(self, scene):
		"""
		Add new scene to the render loop
		"""
		self.scenes.append(scene)

	def next_scene(self):
		"""
		Transition to a new scene and re-initialize the scene
		"""
		print('RenderLoop: next_scene: transitioning scene')
		# Fade out current scene
		effect = self.scene_switch_effect
		self.scene_switch_effect = (effect + 1) % 3
		if effect == 0:
			self.display.dissolve()
		elif effect == 1:
			self.display.fade()
		else:
			self.display.scrollout()

		self.scene_index += 1
		if self.scene_index == len(self.scenes):
			self.scene_index = 0
		i = self.scene_index
		print('RenderLoop: next_scene: selected {}'.format(self.scenes[i].__class__.__name__))
		# (Re-)initialize scene
		self.scenes[i].reset()

	def next_frame(self, button_pressed=0):
		"""
		Display next frame, possibly after a delay to ensure we meet the FPS target
		"""

		scene = self.scenes[self.scene_index]
		if button_pressed:
			# Let the scene handle input
			if scene.input(0, button_pressed):
				# The scene handled the input itself so ignore it
				button_pressed = 0

		t_now = time.ticks_ms() / 1000.0 - self.t_init
		if not self.t_next_frame:
			self.t_next_frame = t_now

		delay = self.t_next_frame - t_now
		if delay >= 0:
			# Wait until we can display next frame
			x = time.ticks_ms() / 1000.0
			time.sleep_ms(int(1000 * delay))
			x = time.ticks_ms() / 1000.0 - x
			if x-delay > 0.01:
				print('RenderLoop: WARN: Overslept when sleeping for {}s, slept {}s more'.format(delay, round(x-delay, 6)))
		else:
			if self.debug:
				print('RenderLoop: WARN: FPS {} might be too high, {}s behind and missed {} frames'.format(self.fps, -delay, round(-delay*self.fps, 2)))
			# Resynchronize
			t_diff = self.fps * (t_now-self.t_next_frame)/self.fps - delay
			if self.debug:
				print('RenderLoop: Should have rendered frame {} at {} but was {}s late'.format(self.frame, self.t_next_frame, t_diff))
			t_diff += 1./self.fps
			self.frame += int(round(self.fps * t_diff))
			self.t_next_frame += t_diff
			if self.debug:
				print('RenderLoop: Will instead render frame {} at {}'.format(self.frame, self.t_next_frame))

		if self.debug:
			print('RenderLoop: Rendering frame {}, next frame at {}'.format(self.frame, round(self.t_next_frame+1./self.fps, 4)))

		# Render current scene
		t = time.ticks_ms() / 1000.0
		loop_again = scene.render(self.frame, self.frame - self.prev_frame - 1, self.fps)
		t = time.ticks_ms() / 1000.0 - t
		if t > 0.1:
			print('RenderLoop: WARN: Spent {}s rendering'.format(t))

		self.scene_switch_countdown -= 1
		if button_pressed or not loop_again or not self.scene_switch_countdown:
			self.reset_scene_switch_counter()
			if not loop_again:
				print('RenderLoop: scene "{}" signalled completion'.format(self.scenes[self.scene_index].__class__.__name__))
			else:
				print('RenderLoop: forcefully switching scenes (button: {}, timer: {}'.format(button_pressed, self.scene_switch_countdown))
			# Transition to next scene
			self.next_scene()
			# Account for time wasted above
			t_new = time.ticks_ms() / 1000.0 - self.t_init
			t_diff = t_new - t_now
			frames_wasted = ceil(t_diff * self.fps)
			#print('RenderLoop: setup: scene switch took {}s, original t {}s, new t {}s, spent {} frames'.format(t_diff, t_now,t_new, self.fps*t_diff))
			self.frame += int(frames_wasted)
			self.t_next_frame += frames_wasted / self.fps

		self.prev_frame = self.frame
		self.frame += 1
		self.t_next_frame += 1./self.fps

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

	# Initialize HAL
	if pycom_board:
		# We're running under MCU here
		print('WLAN: Connecting')
		wlan = WLAN(mode=WLAN.STA)
		wlan.connect(config['ssid'], auth=(WLAN.WPA2, config['password']))
		while not wlan.isconnected():
			machine.idle() # save power while waiting
		time.sleep(1)
		print('WLAN: Connected with IP: {}'.format(wlan.ifconfig()[0]))
		driver = PycomHAL(config)
	else:
		# We're running on the host computer here
		ports = [
			'/dev/tty.usbmodem575711',      # Teensy 3.x on macOS
			'/dev/tty.usbserial-DQ008J7R',  # Pycom device on macOS
			'/dev/ttyUSB0',                 # Linux
			'/dev/ttyACM0',                 # Linux
		]
		for port in ports:
			if os.path.exists(port):
				break
		driver = ArduinoSerialHAL(config)
		driver.set_rtc(time.time() + config['tzOffsetSeconds'])
		driver.set_auto_time(False)
		# Trap Ctrl-C and service termination
		signal.signal(signal.SIGINT, sigint_handler)
		signal.signal(signal.SIGTERM, sigint_handler)


	# Initialize led matrix framebuffer on top of HAL
	num_leds = 256
	rows = 8
	cols = num_leds // rows
	display = LedMatrix(driver, cols, rows, rotation=0)
	driver.clear_display()

	if pycom_board:
		# If we're running on the MCU then loop forever
		while True:
			driver.serial_loop(display)

	# This is where it all begins
	r = RenderLoop(display, fps=10)

	scene = ClockScene(display, config['ClockScene'])
	r.add_scene(scene)

	from weatherscene import WeatherScene
	scene = WeatherScene(display, config['WeatherScene'])
	r.add_scene(scene)

	from animationscene import AnimationScene
	scene = AnimationScene(display, config['AnimationScene'])
	r.add_scene(scene)

	# Render scenes forever
	while True:
		button_pressed = 0
		while True:
			# Drain output from MCU and detect button presses
			line = driver.readline()
			if not line:
				break
			event = line.strip()
			if event == 'BUTTON_SHRT_PRESS':
				button_pressed = 1
			elif event == 'BUTTON_LONG_PRESS':
				button_pressed = 2
			else:
				print('MCU: {}'.format(event))

		r.next_frame(button_pressed)
		if button_pressed:
			button_state = 0
