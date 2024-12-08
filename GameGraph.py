
# Stalker Xray game graph tool
# Author: Stalker tools, 2023-2024


from typing import Iterator
from itertools import islice
# tools imports
from SequensorReader import SequensorReader, OutOfBoundException


class GameGraph:
	'Stalker Xray game graph tool'


	V3D_TYPE = tuple[float, float, float]
	GUID_TYPE = bytes


	def __init__(self, file_path: str):
		self.file_path = file_path
		self._vertex_offset: int | None = None
		self.buff = None
		with open(self.file_path, 'rb') as f:
			self.buff = f.read()
			sr = SequensorReader(self.buff)
			self.version, self.vertex_count, self.edge_count, self.level_point_count = sr.read('BHII')
			self.guid, self.level_count = sr.read_bytes(16), sr.read('B')

	@property
	def vertex_offset(self) -> int:
		if not self._vertex_offset:
			for i in self.iter_levels():
				pass
		return self._vertex_offset

	@property
	def edges_offset(self) -> int:
		return self.vertex_offset + self.vertex_count * SequensorReader.calc_len('ffffffBBBBBBBBIIBB')

	@property
	def points_offset(self) -> int:
		return self.edges_offset + self.edge_count * SequensorReader.calc_len('Hf')

	def iter_levels(self) -> Iterator[tuple[str, V3D_TYPE, int, str, GUID_TYPE]]:
		'iters graph levels (maps)'
		# header
		sr = SequensorReader(self.buff).skip('BHII16sB')
		# levels
		if not self.level_count:
			return
		for _ in range(self.level_count):
			name, offset, id, section = sr.read_string(), sr.read('fff'), sr.read('I'), sr.read_string()
			guid = sr.read_bytes(16)
			yield name, offset, id, section, guid
		self._vertex_offset = sr.pos

	def iter_vertexes(self) -> Iterator[tuple[V3D_TYPE, V3D_TYPE, int, int, tuple[int, int, int, int], int, int, int, int]]:
		'iters graph vertexes'
		sr = SequensorReader(self.buff)
		sr.pos = self.vertex_offset
		if not self.vertex_count:
			return
		for _ in range(self.vertex_count):
			level_point, game_point, level_id = sr.read('fff'), sr.read('fff'), sr.read('B')
			level_vertex_id, vertex_types = sum((x << i * 8 for i, x in enumerate(sr.read('BBB')))), sr.read('BBBB')
			edge_offset, level_point_offset, edge_count, level_point_count = sr.read('IIBB')
			yield level_point, game_point, level_id, level_vertex_id, vertex_types, \
				edge_offset, level_point_offset, edge_count, level_point_count

	def iter_edges(self) -> Iterator[tuple[int, float]]:
		'iters graph edges'
		sr = SequensorReader(self.buff)
		sr.pos = self.edges_offset
		if not self.edge_count:
			return
		for _ in range(self.edge_count):
			game_vertex_id, distance = sr.read('Hf')
			yield game_vertex_id, distance

	def iter_points(self) -> Iterator[tuple[int, float]]:
		'iters graph points'
		sr = SequensorReader(self.buff)
		sr.pos = self.points_offset
		if not self.level_point_count:
			return
		for i in range(self.level_point_count):
			point, (level_vertex_id, distance) = sr.read('fff'), sr.read('If')
			yield point, level_vertex_id, distance

	def get_level_by_id(self, id: int) -> tuple[str, V3D_TYPE, int, str, GUID_TYPE] | None:
		'returns graph level by id (section)'
		level_section = f'el{id:02}'
		if (level := next((x for x in self.iter_levels() if x[3] == level_section), None)):  # get level by index
			return level
		return None


if __name__ == '__main__':
	from sys import argv
	import argparse

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='Stalker Xray game graph tool',
				epilog=f'Examples: {argv[0]} -f ~/.wine/drive_c/Program Files (x86)/GSC World Publishing/S.T.A.L.K.E.R/gamedata/game.graph -l',
			)
			parser.add_argument('-f', metavar='PATH', required=True, help='Game graph file path; example: gamedata/game.graph')
			parser.add_argument('--header', action='store_true', help='Show game graph header')
			parser.add_argument('-l', '--levels', action='store_true', help='Show game levels')
			parser.add_argument('-v', '--vertexes', action='store_true', help='Show game vertexes')
			parser.add_argument('-e', '--edges', action='store_true', help='Show game edges')
			parser.add_argument('-p', '--points', action='store_true', help='Show game points')
			parser.add_argument('--graph-id', metavar='ID', type=int, help='Show level by game vertex index; example: 1240')
			return parser.parse_args()

		def iter(it: Iterator):
			for buff in it():
				print(buff)

		# read command line arguments
		args = parse_args()

		gg = GameGraph(args.f)

		if not args.graph_id is None:
			# find game vertex by index
			if (vertex := next(islice(gg.iter_vertexes(), args.graph_id, args.graph_id + 1))):  # get vertex by index
				if (level := gg.get_level_by_id(vertex[2])):  # get level by id
					print('Level:', level)
				print('Vertex:', vertex)
		if args.header:
			print(gg.version, gg.vertex_count, gg.edge_count, gg.level_point_count, gg.guid, gg.level_count)
		if args.levels:
			iter(gg.iter_levels)
		if args.vertexes:
			iter(gg.iter_vertexes)
		if args.edges:
			iter(gg.iter_edges)
		if args.points:
			iter(gg.iter_points)

	try:
		main()
	except OutOfBoundException: pass
