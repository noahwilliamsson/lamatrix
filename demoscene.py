#!/usr/bin/env python
class DemoScene:
	"""This module implements an example scene with a traveling pixel"""

	def __init__(self, display, config):
		"""
		Initialize the module.
		`display` is saved as an instance variable because it is needed to
		update the display via self.display.put_pixel() and .render()
		"""
		self.display = display
		self.x_pos = 0  # ..just an example
		print('DemoScene: yay, initialized')

	def reset(self):
		"""
		This method is called before transitioning to this scene.
		Use it to (re-)initialize any state necessary for your scene.
		"""
		self.x_pos = 0
		print('DemoScene: here we go')

	def input(self, button_id, button_state):
		"""
		Handle button input
		"""
		print('DemoScene: button {} pressed: {}'.format(button_id, button_state))
		return False  # signal that we did not handle the input

	def render(self, frame, dropped_frames, fps):
		"""
		Render the scene.
		This method is called by the render loop with the current frame number,
		the number of dropped frames since the previous invocation and the
		requested frames per second (FPS).
		"""

		time_in_seconds = frame * fps
		if not time_in_seconds.is_integer():
			# Only update pixel once every second
			return True

		y = 3
		color = 64
		self.display.clear()
		self.display.put_pixel(self.x_pos, y, color, color, color >> 1)
		self.display.render()
		print('DemoScene: rendered a pixel at ({},{})'.format(self.x_pos, y))

		self.x_pos += 1
		if self.x_pos == self.display.columns:
			return False   # our work is done!

		return True   # we want to be called again

if __name__ == '__main__':
	display = None
	config = None
	scene = DemoScene(display, config)
	scene.reset()
