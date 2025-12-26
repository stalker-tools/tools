
# Odyssey/Stalker Xray game Layered File Systems
# Used to work with files from multiple media sources that share one logical files paths tree
# Author: Stalker tools, 2023-2025

from enum import IntEnum
from typing import Protocol, Iterable


class PathType(IntEnum):
	NotExists = 0
	File = 1
	Path = 2


class LayerBase(Protocol):

	def exists(self, path: str, file_wanted: bool = True) -> PathType: return LayeredFileSystem.PathType.NotExists

	def open(self, path: str, mode: str) -> object | None: return None


class LayeredFileSystem:

	def __init__(self, layers: Iterable[LayerBase]):
		self.layers: Iterable[LayerBase] = layers

	def exists(self, path: str, file_wanted: bool = True) -> PathType:
		for layer in self.layers:  # try open file layer by layer
			if (f := layer.exists(path, file_wanted)) and not f.NotExists:
				return f
		return PathType.NotExists

	def open(self, path: str, mode: str = 'r') -> object:
		for layer in self.layers:  # try open file layer by layer
			if (f := layer.open(path, mode)):
				return f


class FileIoBase(Protocol):
	'Protocol for working with binary I/O object.'

	def read(size=-1) -> bytes | None:
		'''Read up to size bytes from the binary I/O object and return them. If size is unspecified or -1, all bytes are returned.
		If 0 bytes or None are returned, and size was not 0, this indicates end of file.
		'''
		...

	def readall(self) -> bytes | None:
		'Read and return all the bytes from the binary I/O object.'
		...

	def write(self, data: bytes) -> int:
		'Write the data to the binary I/O object and return the number of characters written.'
		...
