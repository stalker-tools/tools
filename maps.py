
# Stalker Xray game map (level) files tool
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
# tools imports
from paths import Paths
from ltx_tool import Ltx


class Maps:

	def __init__(self, gamedata_path: str) -> None:
		self.paths = Paths(gamedata_path)
		self.global_map: Ltx.Section | None = None
		self.maps: tuple[Ltx.Section] | None = None
		self.load_maps()

	def iter_sections(self, ltx: Ltx) -> Iterator[Ltx.Section]:
		if ltx:
			for section in ltx.iter_sections():
				yield section
			for ltx in ltx.ltxs:
				for section in ltx.iter_sections():
					yield section

	def load_maps(self) -> tuple[str] | None:
		'return maps names'
		self.maps = self.global_map = None
		maps_names = None
		maps: list[Ltx.Section] = []
		# load global map and maps names sections
		for section in self.iter_sections(Ltx(self.paths.game_ltx)):
			match section.name:
				case 'level_maps_single':
					maps_names = tuple(map(str.lower, section.iter_names()))
				case 'global_map':
					self.global_map = section
			if maps_names and self.global_map:
				break
		# load maps sections
		if maps_names:
			for section in self.iter_sections(Ltx(self.paths.game_ltx)):
				if section.name.lower() in maps_names:
					maps.append(section)
					if len(maps) == len(maps_names):
						break  # all maps sections loaded
		if maps:
			self.maps = tuple(maps)

	def iter_maps_sections(self) -> Iterator[Ltx.Section]:
		if self.global_map:
			yield self.global_map
		if self.maps:
			for section in self.maps:
				yield section

	def get_map_section(self, map_name: str) -> Ltx.Section | None:
		'returns map .ltx file section'
		if (section := next((x for x in self.iter_maps_sections() if x.name == map_name), None)):
			return section
		return None

	def get_image_file_path(self, section: Ltx.Section) -> str | None:
		'returns map image file path'
		if section and (texture := section.get('texture')):
			return self.paths.join(self.paths.gamedata, 'textures', texture+'.dds')
		return None
