
# Stalker Xray game map (level) files tool
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
from PIL.Image import open as image_open, Image
# stalker-tools import
from version import PUBLIC_VERSION, PUBLIC_DATETIME
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from ltx_tool import Ltx
from localization import Localization
from icon_tools import get_image_as_html_img


class Maps:

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



		def analyse(paths: Paths):
			loc = Localization(paths)
			maps = Maps(paths, loc)

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

			if verbose:
				print('<h2>Maps .ltx:<pre>')
				for ltx_section in maps.iter_maps_sections():
					print(str(ltx_section))
					print(maps.get_image_file_path(ltx_section))
				print('</pre></h2>')

			print('<h2>Table of contents</h2>')
			for i, ltx_section in enumerate(maps.iter_maps_sections()):
				print(f'<h3><a href="#{ltx_section.name}">{i+1} {maps.get_localized_name(ltx_section)}</a></h3>')

			# show maps names and images
			print('<hr/><h2>Maps</h2')
			for i, ltx_section in enumerate(maps.iter_maps_sections()):
				print(f'<h3><a name="{ltx_section.name}"></a>{i+1} {maps.get_localized_name(ltx_section)}<p>')
				if (map_texture_filepath := maps.get_image_file_path(ltx_section)):
					if verbose:
						print(f'<pre>{map_texture_filepath}</pre>')
					if (map_image := maps.get_image(ltx_section)):
						print(get_image_as_html_img(map_image))
				else:
					print('NO IMAGE')
				print('</p></h3>')

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
				verbose=verbose,
				exclude_gamedata=args.exclude_gamedata)

		paths = Paths(paths_config)

		analyse(paths)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
