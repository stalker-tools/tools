
from collections.abc import Iterator
from SequensorReader import SequensorReader


class ChunkReader:

	def __init__(self, buff: bytes) -> None:
		self.sr = SequensorReader(buff)

	def iter(self) -> Iterator[int, int, bytes]:
		'''
		iterate chunks
		yields: type, size, bytes
		'''
		self.sr.pos = 0
		while self.sr.pos < len(self.sr.buff):
			type, size = self.sr.read('II')
			yield type, size, self.sr.read_bytes(size)
