# Render a box with up to three animations
#
import time
from icon import Icon

class AnimationScene:
	"""Render animations from https://developer.lametric.com"""

	def __init__(self, display, config):
		self.display = display
		self.debug = False
		self.intensity = 16
		self.icons = []
		self.icon_id = 0
		self.states = []
		self.on_screen_icons = []
		if not config:
			return
		if 'debug' in config:
			self.debug = config['debug']
		if 'intensity' in config:
			self.intensity = int(round(config['intensity']*255))
		if 'icons' in config:
			for filename in config['icons']:
				self.add_icon(filename)
		self.set_intensity(self.intensity)

	def reset(self):
		while self.load_icon():
			pass

	def set_intensity(self, value=None):
		if value is not None:
			self.intensity -= 1
			if not self.intensity:
				self.intensity = 16
			for i in self.icons:
				i.set_intensity(self.intensity)
		return self.intensity

	def input(self, button_state):
		"""
		Handle button input
		"""
		return 0  # signal that we did not handle the input

	def render(self, frame, dropped_frames, fps):
		t0 = time.time()
		display = self.display
		intensity = self.intensity
		unload_queue = []
		for state in self.on_screen_icons:
			if frame < state['next_frame_at']:
				continue

			state['remaining_frames'] -= 1
			if state['remaining_frames'] == 0:
				# Queue icon for removal from screen
				unload_queue.append(state['i'])

			n = state['num_frames']
			index = n - (state['remaining_frames'] % n) - 1
			x_pos = state['x_pos']
			y_pos = state['y_pos']
			icon = self.icons[state['i']]
			# Do not repaint until some specified time in the future
			state['next_frame_at'] = frame + int(fps * icon.frame_length() / 1000)
			# Render icon
			icon.blit(self.display, x_pos, y_pos)

		t2 = time.time()
		t1 = t2 - t0
		display.render()
		t3 = time.time()
		t2 = t3 - t2
		if self.debug:
			print('AnimationScene: Spent {}ms plotting icons, {}ms updating LedMatrix+HAL, {}ms total'.format(round(t1*1000.0), round(t2*1000.0), round((t3-t0)*1000.0)))

		for i in unload_queue:
			self.unload_icon(i)

		if not self.on_screen_icons:
			return False  # Nothing more to display

		return True  # We still have icons left to render

	def add_icon(self, filename):
		"""
		See animations/README.md for details
		"""
		icon = Icon(filename)
		self.icons.append(icon)

	def load_icon(self):
		"""
		Load icon into first available slot
		"""
		cols = bytearray(b' ' * 32)
		icon_width = 8
		padding = 1 if self.display.columns == 32 else 0
		for state in self.on_screen_icons:
			icon_x = state['x_pos'] + (state['y_pos']<<1)
			cols[icon_x:icon_x+icon_width] = ('x'*icon_width).encode()

		x = 0
		space = ord(' ')
		need = icon_width+padding
		for i in range(32):
			if cols[i] != space:
				x = i+1
			elif i+1 == x+need:
				break
		if i+1 != x+need:
			# no available space
			return False
		if not x:
			# center for 32x8 displays
			x += 3 if self.display.columns == 32 else 0
		else:
			# left-pad next icon
			x += padding

		icon = self.icons[self.icon_id]
		num_frames = icon.frame_count()
		state = {
			'i': self.icon_id,               # for unloading the icon
			'x_pos': x if self.display.columns == 32 else x & 0xf,
			'y_pos': 0 if self.display.columns == 32 else (x >> 4) << 3,
			'num_frames': num_frames,        # cached for convenience
			'remaining_frames': num_frames,  # keep track of the currently rendered frame
			'next_frame_at': 0               # for handling delays
		}

		# Ensure a minimum display time
		t_icon = icon.length_total()
		for i in range(1,6):
			if t_icon*i >= 4000:
				break
			state['remaining_frames'] += num_frames

		self.on_screen_icons.append(state)
		if self.debug:
			print('Animation: loaded icon {} at ({}, {})'.format(self.icon_id, state['x_pos'], state['y_pos']))
		self.icon_id = (self.icon_id + 1) % len(self.icons)
		return True

	def unload_icon(self, i):
		display = self.display
		for state in self.on_screen_icons:
			if state['i'] == i:
				icon = self.icons[i]
				height = icon.rows
				width = icon.cols
				x_pos = state['x_pos']
				y_pos = state['y_pos']
				for y in range(height):
					for x in range(width):
						display.put_pixel(x_pos+x, y_pos+y, 0, 0, 0)
				self.on_screen_icons.remove(state)
				return

