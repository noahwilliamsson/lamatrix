try:
	from ustruct import unpack_from
except ImportError:
	from struct import unpack_from

class Icon:
	def __init__(self, filename, intensity_bits=4):
		self.f = open(filename, 'rb')
		self.intensity_bits = intensity_bits
		self.frame = 0
		chunk = bytearray(4)
		self.f.readinto(chunk)
		self.num_frames = chunk[0]
		self.rows = chunk[1]
		self.cols = chunk[2]
		self.buf = bytearray(self.rows*self.cols*3)
		self.delays = [0] * self.num_frames
		chunk = self.f.read(self.num_frames*2)
		for i in range(self.num_frames):
			self.delays[i] = unpack_from('!h', chunk, i*2)[0]
		self.frame_offset = self.f.tell()

	def frame_count(self):
		return self.num_frames

	def frame_length(self):
		return self.delays[self.frame]

	def length_total(self):
		return sum(self.delays)

	def reset(self):
		self.frame = 0
		self.f.seek(self.frame_offset)

	def set_intensity(self, intensity):
		if intensity >= 128:
			self.intensity_bits = 7
		elif intensity >= 64:
			self.intensity_bits = 6
		elif intensity >= 32:
			self.intensity_bits = 5
		elif intensity >= 16:
			self.intensity_bits = 4
		elif intensity >= 8:
			self.intensity_bits = 3
		elif intensity >= 4:
			self.intensity_bits = 2
		elif intensity >= 2:
			self.intensity_bits = 1

	def blit(self, display, x, y):
		self.f.readinto(self.buf)
		bits_to_drop = 8 - self.intensity_bits
		buf = self.buf
		for i in range(len(self.buf)):
			buf[i] >>= bits_to_drop
		display.render_block(self.buf, self.rows, self.cols, x, y)
		self.frame += 1
		if self.frame == self.num_frames:
			self.reset()

	def close(self):
		"""
		MicroPython do not call __del__ so we need a manual destructor
		"""
		self.f.close()
