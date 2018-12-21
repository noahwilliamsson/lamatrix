#!/usr/bin/env python
#
import time
import json

class AnimationScene:
	"""Render animations from https://developer.lametric.com"""

	def __init__(self, display, config):
		self.name = 'Animation'
		self.display = display
		self.objs = []
		self.obj_i = 0
		self.states = []
		self.on_screen_objs = []
		if config and 'files' in config:
			for filename in config['files']:
				self.add_obj(filename)

	def add_obj(self, filename):
		# This method expects an animation as downloaded from LaMetric's developer site
		#
		# Example:
		#   curl -sA '' https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=4007 > blah.json
		#
		# To get an index of available animations, try:
		#   curl -sA '' 'https://developer.lametric.com/api/v1/dev/preloadicons?page=1&category=popular&search=&count=5000' | tee popular-24k-p1.json
		#
		with open(filename) as f:
			data = f.read()
		obj = json.loads(data)
		obj = json.loads(obj['body'])
		self.objs.append(obj)

	def reset(self):
		print('Animation: reset called, loading animation objects')
		while self.load_obj():
			pass

	def input(self, button_id, button_state):
		"""
		Handle button input
		"""
		print('Animation: button {} pressed: {}'.format(button_id, button_state))
		return False  # signal that we did not handle the input

	def load_obj(self):
		"""
		Load object into first available slot
		"""
		cols = bytearray(' ' * 32)
		obj_width = 8
		padding = 1
		for state in self.on_screen_objs:
			obj_x = state['x_pos']
			cols[obj_x:obj_x+obj_width] = ('x'*obj_width).encode()
		x = cols.find(' ' * (obj_width + padding))
		if x < 0:
			# no available space
			print('Animation: not enough columns to add another object')
			return False
		if not x:
			# center
			x += 3
		else:
			# left-pad next animation
			x += padding

		obj = self.objs[self.obj_i]
		num_frames = len(obj['icons'])
		state = {
			'i': self.obj_i,  # for unloading the object
			'x_pos': x,
			'frames': obj['icons'],
			'frame_delay_ms': obj['delays'],
			'num_frames': num_frames,           # cached for convenience
			'remaining_frames': 2*num_frames,   # keep track of the currently rendered frame
			'next_frame_at': 0                  # for handling delays
		}
		self.on_screen_objs.append(state)
		print('Animation: loaded object {} at column {}'.format(self.obj_i, x))
		self.obj_i = (self.obj_i + 1) % len(self.objs)
		return True

	def unload_obj(self, i):
		display = self.display
		for state in self.on_screen_objs:
			if state['i'] == i:
				height = len(state['frames'][0])
				width = len(state['frames'][0][0])
				x_pos = state['x_pos']
				for y in range(height):
					for x in range(width):
						display.put_pixel(x_pos+x, y, 0, 0, 0)
				self.on_screen_objs.remove(state)
				print('Animation: unloaded object {} from column {}'.format(i, x_pos))
				return

	def render(self, frame, dropped_frames, fps):
		t0 = time.time()
		display = self.display
		unload_queue = []
		for state in self.on_screen_objs:
			if frame < state['next_frame_at']:
				continue

			state['remaining_frames'] -= 1
			if state['remaining_frames'] == 0:
				# Queue object for removal
				unload_queue.append(state['i'])

			n = state['num_frames']
			index = n - (state['remaining_frames'] % n) - 1
			data = state['frames'][index]
			x_pos = state['x_pos']
			for y in range(len(data)):
				row = data[y]
				for x in range(len(row)):
					r = round(row[x][0] * 255)
					g = round(row[x][1] * 255)
					b = round(row[x][2] * 255)
					display.put_pixel(x_pos+x, y, r, g, b)
			# Do not repaint until some spe
			state['next_frame_at'] = frame + int(fps * state['frame_delay_ms'][index] / 1000)
			print('AnimationScene: obj {}: queueing repaint at frame {}+{}=={}, fps {}, delay {}'.format(state['i'], frame, int(fps * state['frame_delay_ms'][index] / 1000), state['next_frame_at'], fps, state['frame_delay_ms'][index]))
		t1 = time.time() - t0

		t2 = time.time()
		display.render()
		t3 = time.time() - t2
		print('AnimationScene: Spent {}ms plotting objects, {}ms updating LedMatrix+HAL, {}ms total'.format(round(1000*t1), round(1000*t2), round(1000*(time.time()-t0))))

		for i in unload_queue:
			self.unload_obj(i)

		if not self.on_screen_objs:
			# Nothing more to display
			return False
		# We still have objects left to render
		return True
