
from typing import Literal
from struct import Struct


class OutOfBoundException(Exception):
	pass


class SequensorReader:

	def __init__(self, buff: bytes, byte_order: Literal['<', '>', '=', '!', '@'] = '<') -> None:
		'''
		byte_order:	Struct format byte order: < - little-endian; > - big-endian; = - native; ! - network; @ - string native
		'''
		self.buff, self.byte_order = buff, byte_order
		self.pos = 0
	
	def read(self, format: str) -> tuple[int | float] | int | float:
		'''
		reads according to Struct format
		format:	see struct help - Format Characters
		'''
		s = Struct(self.byte_order+format)
		_size = s.size
		if self.pos + _size > len(self.buff):
			raise OutOfBoundException()
		ret = s.unpack(self.buff[self.pos:self.pos+_size])
		self.pos += _size
		return ret[0] if len(ret) == 1 else ret

	def read_string(self) -> str:
		'''
		reads null-terminated string
		'''
		string_end_index = self.buff.find(b'\0', self.pos)
		if string_end_index < 0:
			raise OutOfBoundException()
		ret = self.buff[self.pos:string_end_index].decode()
		self.pos = string_end_index + 1  # after null byte
		return ret

	def read_bytes(self, size: int | None = None, *, update_position = True) -> bytes:
		'''
		reads bytes
		size:	size to read, bytes; None - read until buffer end
		'''
		if size is None:
			ret = self.buff[self.pos:]
			if update_position:
				self.pos = len(self.buff) + 1
			return ret
		ret = self.buff[self.pos:self.pos+size]
		if len(ret) != size:
			raise OutOfBoundException()
		if update_position:
			self.pos += size
		return ret

	@property
	def remain(self) -> int:
		'returns remaining bytes count'
		return len(self.buff) - self.pos
