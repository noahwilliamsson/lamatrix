# The game looop
import time
import gc
from math import ceil

if not hasattr(time, 'sleep_ms') or not hasattr(time, 'ticks_ms'):
	# Emulate https://docs.pycom.io/firmwareapi/micropython/utime.html
	time.ticks_ms = lambda: int(time.time() * 1000)
	time.sleep_ms = lambda x: time.sleep(x/1000.0)


class RenderLoop:
	def __init__(self, display, config=None):
		self.display = display
		self.debug = False
		self.fps = display.fps
		self.t_next_frame = None
		self.prev_frame = 0
		self.frame = 1
		self.t_init = time.ticks_ms()
		self.scenes = []
		self.scene_index = 0
		self.scene_switch_effect = 0
		self.scene_switch_countdown = self.fps * 40
		self.display.clear()
		if not config:
			return
		if 'debug' in config:
			self.debug = config['debug']
		if 'sceneTimeout' in config:
			self.scene_switch_countdown = self.fps * config['sceneTimeout']

	def add_scene(self, scene):
		"""
		Add new scene to the render loop.
		Called by main.py.
		"""
		self.scenes.append(scene)

	def next_frame(self, button_state=0):
		"""
		Display next frame, possibly after a delay to ensure we meet the FPS target
		Called by main.py.
		"""

		scene = self.scenes[self.scene_index]
		# Process input
		if button_state:
			# Let the scene handle input
			handled_bit = scene.input(button_state)
			button_state &= ~handled_bit
			# Use long-pressed buttons to handle intensity changes
			if button_state & 0x22:
				clear = 0
				for s in self.scenes:
					if hasattr(s, 'set_intensity'):
						i = s.set_intensity()
						if button_state & 0x02:
							i -= 2
							clear = 0x02
						elif button_state & 0x20:
							i += 2
							clear = 0x20
						i = (i + 32) % 32
						s.set_intensity(i)
				button_state &= ~clear
				if self.debug:
					print('RenderLoop: updated intensity to {} on scenes, remaining state: {}'.format(i, button_state))

		# Calculate how much we need to wait before rendering the next frame
		t_now = time.ticks_ms() - self.t_init
		if not self.t_next_frame:
			self.t_next_frame = t_now

		delay = self.t_next_frame - t_now
		if delay >= 0:
			# Wait until we can display next frame
			time.sleep_ms(delay)
		else:
			# Resynchronize
			num_dropped_frames = ceil(-delay*self.fps/1000)
			if self.debug:
				print('RenderLoop: FPS {} too high, should\'ve rendered frame {} at {}ms but was {}ms late and dropped {} frames'.format(self.fps, self.frame, self.t_next_frame, -delay, num_dropped_frames))
			self.frame += num_dropped_frames
			self.t_next_frame += ceil(1000*num_dropped_frames/self.fps)
			if self.debug:
				print('RenderLoop: Updated frame counters to frame {} with current next at {}'.format(self.frame, self.t_next_frame))

		# Let the scene render its frame
		t = time.ticks_ms()
		loop_again = scene.render(self.frame, self.frame - self.prev_frame - 1, self.fps)
		t = time.ticks_ms() - t
		if t > 1000/self.fps and self.debug:
			print('RenderLoop: WARN: Spent {}ms rendering'.format(t))


		# Consider switching scenes and update frame counters
		self.scene_switch_countdown -= 1
		scene_increment = 1
		if not loop_again:
			self.scene_switch_countdown = 0
		elif button_state:
			self.scene_switch_countdown = 0
			if button_state & 0x1:
				scene_increment = -1

		if not self.scene_switch_countdown:
			self.reset_scene_switch_counter()
			# Transition to next scene
			self.next_scene(scene_increment, button_state)
			# Account for time wasted above
			t_new = time.ticks_ms() - self.t_init
			t_diff = t_new - t_now
			frames_wasted = ceil(t_diff*self.fps/1000.0)
			if self.debug:
				print('RenderLoop: setup: scene switch took {}ms, original t {}ms, new t {}ms, spent {} frames'.format(t_diff, t_now,t_new, self.fps*t_diff/1000.0))
			self.frame += int(frames_wasted)
			self.t_next_frame += int(1000.0 * frames_wasted / self.fps)

		self.prev_frame = self.frame
		self.frame += 1
		self.t_next_frame += int(1000/self.fps)

	def reset_scene_switch_counter(self):
		"""
		Reset counter used to automatically switch scenes.
		The counter is decreased in .next_frame()
		"""
		self.scene_switch_countdown = 45 * self.fps

	def next_scene(self, increment=1, button_state=0):
		"""
		Transition to a new scene and re-initialize the scene
		"""
		if len(self.scenes) < 2:
			return

		print('RenderLoop: next_scene: transitioning scene')
		# Fade out current scene
		t0 = time.ticks_ms()
		if button_state & 0x01:
			self.display.hscroll(-4)
			button_state &= ~0x01
		elif button_state & 0x10:
			self.display.hscroll(4)
			button_state &= ~0x10
		else:
			effect = self.scene_switch_effect
			self.scene_switch_effect = (effect + 1) % 4
			if effect == 0:
				self.display.vscroll()
			elif effect == 1:
				self.display.hscroll()
			elif effect == 2:
				self.display.fade()
			else:
				self.display.dissolve()

		t2 = time.ticks_ms()
		t1 = t2 - t0
		gc.collect()

		t3 = time.ticks_ms()
		t2 = t3 - t1
		num_scenes = len(self.scenes)
		i = self.scene_index = (num_scenes + self.scene_index + increment) % num_scenes
		# (Re-)initialize scene
		self.scenes[i].reset()
		t4 = time.ticks_ms()
		t3 = t4 - t3
		if self.debug:
			print('RenderLoop: next_scene: selected {}, effect {}ms, gc {}ms, scene reset {}ms, total {}ms'.format(self.scenes[i].__class__.__name__, t1, t2, t3, t4-t0))
		return button_state
