
# Stalker Xray game map (level) files tool
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
from typing import Iterator, NamedTuple, Self
from PIL.Image import open as image_open, Image
# stalker-tools import
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from ltx_tool import Ltx
from localization import Localization
from icon_tools import get_image_as_html_img


class Pos2d(NamedTuple):
	'X-ray 2D Point'
	x: float
	y: float


class Pos3d(NamedTuple):
	'X-ray 3D Point'
	x: float
	y: float
	z: float

	@property
	def pos2d(self) -> Pos2d:
		return Pos2d(self.x, self.z)


class Rect(NamedTuple):
	'X-ray Map 2D Rect'
	x: float
	y: float
	width: float
	heigth: float

	@classmethod
	def from_two_points(cls, x1: float | str, y1: float | str, x2: float | str, y2: float | str) -> Self:
		'returns Rect from points: left top and right down'
		x1, y1 = float(x1), float(y1)
		x2, y2 = float(x2), float(y2)
		return Rect(x1, y1, x2 - x1, y2 - y1)


class Point(NamedTuple):
	'image point'
	x: int
	y: int



class Maps:


	class Map:
		'helper class (wrapper) for map'
		__slots__ = ('maps', 'section', '_image_size')

		def __init__(self, maps: 'Maps', section: Ltx.Section):
			self.maps = maps
			self.section = section
			self._image_size: Point | None = None

		@property
		def name(self) -> str:
			return self.section.name

		@property
		def localized_name(self) -> str:
			if (ret := self.maps.get_localized_name(self.section)):
				return ret  # localized name
			return self.name  # not localized name

		@property
		def image(self) -> Image | None:
			if (image := self.maps.get_image(self.section)):
				if not self._image_size:
					self._image_size = Point(*image.size)
				return image

		@property
		def rect(self) -> Rect | None:
			'returns map (level) coordinates rect'
			if (bound_rect := self.section.get('bound_rect')):
				return Rect.from_two_points(*bound_rect)
			return None

		def coord_to_image_point(self, pos: Pos2d) -> Point:
			if not self._image_size:
				self.image
			if (rect := self.rect) and (size := self._image_size):
				dx, dy = rect.width / size.x, rect.heigth / size.y
				return Point((pos.x - rect.x) / dx, size.y - (pos.y - rect.y) / dy)


	def __init__(self, paths: Paths, loc: Localization | None = None) -> None:
		self.paths = paths
		self.global_map: Ltx.Section | None = None
		self.maps: tuple[Ltx.Section] | None = None
		self.loc = loc
		self._load_maps()

	def _load_maps(self) -> tuple[str] | None:
		'return maps names'

		def _iter_sections(ltx: Ltx) -> Iterator[Ltx.Section]:
			if ltx:
				for section in ltx.iter_sections():
					yield section
				for ltx in ltx.ltxs:
					for section in ltx.iter_sections():
						yield section

		self.maps = self.global_map = None
		maps_names = None
		maps: list[Ltx.Section] = []
		# load global map and maps names sections
		for section in _iter_sections(Ltx(self.paths.game_ltx, open_fn=self.paths.open)):
			match section.name:
				case 'level_maps_single':
					maps_names = tuple(map(str.lower, section.iter_names()))
				case 'global_map':
					self.global_map = section
			if maps_names and self.global_map:
				break
		# load maps sections
		if maps_names:
			for section in _iter_sections(Ltx(self.paths.game_ltx, open_fn=self.paths.open)):
				if section.name.lower() in maps_names:
					maps.append(section)
					if len(maps) == len(maps_names):
						break  # all maps sections loaded
		if maps:
			self.maps = tuple(maps)

	def iter_maps(self) -> Iterator[Map]:
		for ltx in self.iter_maps_sections():
			yield self.Map(self, ltx)

	def get_map(self, map_name: str) -> Map | None:
		if (ltx := self.get_map_section(map_name)):
			return self.Map(self, ltx)
		return None

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
			return self.paths.join('textures', texture+'.dds')
		return None

	def get_localized_name(self, section: Ltx.Section) -> str | None:
		if self.loc:
			return self.loc.get(section.name, True)
		return None

	def get_image(self, section: Ltx.Section) -> Image | None:
		if (map_texture_filepath := self.get_image_file_path(section)):
			with self.paths.open(map_texture_filepath, 'rb') as f:
				return image_open(f)
		return None


if __name__ == '__main__':
	from sys import argv, exit
	import argparse
	from pathlib import Path
	from os.path import basename
	from typing import NamedTuple

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray maps .ltx file parser.
Out format: html with maps images embedded.

Note:
It is not necessary to extract .db/.xdb files to gamedata path. This utility can read all game files from .db/.xdb files !
''',
				epilog=f'''Examples:
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru --head "SoC" > "SoC.maps.html"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', help='game root path (with .db/.xdb files); default: current path')
			parser.add_argument('--exclude-db-files', metavar='FILE_NAME|PATTERN', nargs='+',
				help='game path that contains .db/.xdb files and optional gamedata folder; Unix shell-style wildcards: *, ?, [seq], [!seq]')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('--exclude-gamedata', action='store_true', help='''exclude files from gamedata sub-path;
used to get original game (.db/.xdb files only) infographics; default: false
''')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			parser.add_argument('-f', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata directory path; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus',
				help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; dump .ltx sections; example: -v')
			return parser.parse_args()


		class LightStyle(NamedTuple):
			page_bgcolor: str = '#e8f1ec'
			bgcolor: str = '#e8f1ec40'
			color: str = 'black'


		class DarkStyle(NamedTuple):
			page_bgcolor: str = '#25252a'
			bgcolor: str = '#20202030'
			color: str = '#c2c7c6'



		def analyse(paths_config: PathsConfig):
			# define style for html
			match args.style.lower():
				case 'l':
					style = LightStyle()
				case _:
					style = DarkStyle()

			# open html body
			print(f'<html>\n<head><title>{args.head}</title></head>')
			print(f'<body style="background-color:{style.page_bgcolor};color:{style.color};">')
			print(f'<h1>{args.head}</h1><hr/>')

			# Paths load log
			if verbose:
				print('<h2>Paths log:</h2><pre>')
			paths = Paths(paths_config)
			if verbose:
				print('</pre>')

			# Localization load log
			if verbose:
				print('<h2>Localization log:</h2><pre>')
			loc = Localization(paths, paths.config.verbose)
			maps = Maps(paths, loc)
			if verbose:
				print('</pre>')

			# dump maps .ltx
			if verbose:
				print('<h2>Maps .ltx:</h2><pre>')
				for ltx_section in maps.iter_maps_sections():
					print(str(ltx_section))
					print(maps.get_image_file_path(ltx_section))
				print('</pre><hr/>')

			# Table of contents
			print('<h2>Table of contents</h2>')
			for i, map in enumerate(maps.iter_maps()):
				print(f'<h3><a href="#{map.name}">{i+1} {map.localized_name}</a></h3>')

			# show maps names and images
			print('<hr/><h2>Maps</h2')
			for i, map in enumerate(maps.iter_maps()):
				print(f'<h3>{i+1} {map.name+" / " if verbose else ""}<a name="{map.name}"></a>{map.localized_name}<p>')
				if verbose and (map_texture_filepath := maps.get_image_file_path(map.section)):
					print(f'<pre>{map_texture_filepath}</pre>')
				if (image := map.image):
					print(get_image_as_html_img(image))
				else:
					print('NO IMAGE')

			# close html body
			print('</body>\n</html>')

		args = parse_args()
		verbose = args.v

		gamepath = Path(args.gamepath) if args.gamepath else Path()
		paths_config = None
		if gamepath:
			if not args.version:
				raise ValueError(f'Argument --version or -t is missing; see help: {argv[0]} -h')
			paths_config = PathsConfig(
				gamepath.absolute().resolve(), args.version,
				args.gamedata,
				exclude_db_files=args.exclude_db_files,
				verbose=verbose,
				exclude_gamedata=args.exclude_gamedata)

		analyse(paths_config)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
