#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Main class for Stalker X-ray and Odyssey game files
# It have command-line interface
# Author: Stalker tools, 2023-2026

from typing import Iterator, NamedTuple
from configparser import ConfigParser
from pathlib import Path
from itertools import islice
from PIL import ImageDraw, ImageColor
from PIL.Image import open as image_open, Image
# stalker-tools import
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from fsgame import parse as fsgame_parse
from GameConfig import GameConfig, Ltx
from GameGraph import GameGraph
from maps_tool import Maps, Pos3d
from icon_tools import IconsEquipment, UiNpcUnique, UiIconstotal, get_image_as_html_img
from save_tool import Save
from paths import Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from DBReader import UnspecifiedDbFormat
from ltx_tool import Ltx


DEFAULT_TITLE = 'Stalker'
DEFAULT_AUTHOR = 'stalker-tools'
DEFAULT_LOCALIZATION = 'ru'
DEFAULT_FSGAME_FILE_NAME = 'fsgame.ltx'
DEFAULT_GAMEDATA = 'gamedata'
DEFAULT_ODYSSEY_CONFIG_FILE_NAME = 'odyssey.ini'
DEFAULT_ODYSSEY_PATH = 'odyssey'


class Game:
	'''
	Xray game config: .ltx, .xml localization, items images (icons), maps (levels), game.graph
	Odyssey game config (if any): .ini
	Xray gameplay: fsgame.ltx, .sav savings
	'''


	class GameBaseException(Exception): pass
	class FsgameFileNotFoundError(GameBaseException): pass
	class SavFileNotFoundError(GameBaseException): pass


	class Config:
		'''
		game_config: GameConfig  # game .ltx files; loads from gamedata folder
		odyssey_path: Path  # odyssey path; path that contains python files and profiles for web interface
		title: str  # odyssey title; comes from odyssey.ini
		author: str  # odyssey author; comes from odyssey.ini
		maps: Maps  # game maps .ltx files; loads from gamedata folder
		icons: IconsEquipment  # game icons; loads from gamedata folder
		'''

		def __init__(self, game_config: GameConfig, odyssey_config_file_name: str = DEFAULT_ODYSSEY_CONFIG_FILE_NAME,
			   fsgame_file_name: str = DEFAULT_FSGAME_FILE_NAME):
			# check game path
			self.game_config = game_config
			# load configs
			self._read_odyssey_config(odyssey_config_file_name)  # load odyssey config
			self._read_fsgame(fsgame_file_name)  # load stalker config

		def _read_odyssey_config(self, odyssey_config_file_name: str) -> None:
			'reads odyssey.ini file'
			self.odyssey_config_file_path = Path(odyssey_config_file_name)
			if not self.odyssey_config_file_path.is_absolute():
				self.odyssey_config_file_path = self.game_config.paths.path / odyssey_config_file_name
			if self.game_config.verbose:
				print(f'Load odyssey config file: {self.odyssey_config_file_path}')
			self.odyssey_config = ConfigParser()
			self.odyssey_config.read(self.odyssey_config_file_path)
			self.title = self.odyssey_config.get('global', 'title', fallback=None) or DEFAULT_TITLE
			self.author = self.odyssey_config.get('global', 'author', fallback=None) or DEFAULT_AUTHOR
			self.odyssey_path = self.game_config.paths.path / (self.odyssey_config.get('odyssey', 'path', fallback=None) or DEFAULT_ODYSSEY_PATH)

		def _read_fsgame(self, fsgame_file_name: str) -> None:
			'reads fsgame.ltx file'
			self.fsgame_file_path = self.game_config.paths.path / fsgame_file_name
			if self.game_config.verbose:
				print(f'Load fsgame.ltx file: {self.fsgame_file_path}')
			try:
				self.fsgame = fsgame_parse(self.fsgame_file_path)
			except FileNotFoundError as e:
				raise Game.FsgameFileNotFoundError from e

		def iter_map_sections(self) -> Iterator[Ltx.Section]:
			'iterates game maps .ltx file sections'
			if self.maps.maps:
				for section in self.maps.maps:
					yield section

		def iter_map_names(self) -> Iterator[str]:
			'iterates game maps names'
			for section in self.iter_map_sections():
				yield section.name


	class Save:
		'Save .sav file'


		class Object:
			'Save .sav file object from ObjectChunk'

			def __init__(self, save: 'Game.Save', raw_object: dict[str, any], section: Ltx.Section):
				self.save = save
				self.raw_object = raw_object
				self.section = section

			@property
			def image(self) -> Image | None:
				'returns icon'
				try:
					return self.save.game.icons_equipment.get_image(
						int(self.section.get('inv_grid_x')), int(self.section.get('inv_grid_y')),
						int(self.section.get('inv_grid_width', 1)), int(self.section.get('inv_grid_height', 1)))
				except ValueError:
					return None

			@property
			def pos(self) -> Pos3d | None:
				'returns "position"'
				if (position := self.raw_object.get('position')):
					return Pos3d(position)
				return None


		def __init__(self, game: 'Game', name: str):
			'''Game save .sav file
			name - save name, .sav file name stem
			raises Game.SavFileNotFoundError
			'''

			self.game: Game = game
			self.name = name
			self.file_path: Path | None = self.game.get_save_file_path(self.name)
			if self.file_path is None:
				raise Game.SavFileNotFoundError()

		@property
		def screenshot_image(self) -> Image | None:
			if (save_file_path := self.file_path):
				try:
					return image_open(save_file_path.with_suffix('.dds'))
				except FileNotFoundError: pass
			return None

		@property
		def map(self) -> Maps.Map | None:
			'''returns Map from .sav file actor position
			Use actor graph id according to Game Graph to get map (level) name
			'''
			if (actor := self.actor_object_raw):  # get actor from .sav
				if (graph_id := actor.get('graph_id')) is not None:  # get Game Graph of actor from .sav
					# get map (level) name from Game Graph
					if (map := self.game.get_map_by_graph_map_name(self.game.get_map_name_by_graph(graph_id))):
						return map
			return None

		def iter_actor_objects_raw(self, actor_only = False) -> Iterator[dict]:
			'''iterates .sav file for actor object or belongs to actor objects
			actor_only - True: actor object; False: actor and belongs to actor objects
			'''
			gs = Save(self.file_path)  # Game Save
			for chunk in gs.iter_chunks():
				if chunk.type == Save.ChunkTypes.OBJECT:
					for data in chunk.iter_data():
						if data.get('id') == 0:
							# actor object
							yield data
							if actor_only:
								return
						elif data.get('id_parent') == 0 and not actor_only:
							# belongs to actor object
							yield data

		def iter_actor_objects(self) -> 'Iterator[Game.Save.Object]':
			'iterates .sav file for belongs to actor objects'
			for raw_object in self.iter_actor_objects_raw():  # iter .sav actor object and his objects
				if raw_object.get('name') != 'actor':  # skip actor
					# if (section := self.game.config.game_config.find_section_system_ltx(raw_object.get('name'))):  # get .ltx section
					if (section := self.game.config.game_config.find(raw_object.get('name'))):  # get .ltx section
						yield self.Object(self, raw_object, section)

		def has_actor_object(self, object_name: str) -> bool:
			for object in self.iter_actor_objects_raw():
				if object.get('name') == object_name:
					return True

		@property
		def actor_object_raw(self) -> dict[str, any]:
			'returns actor object from .sav file'
			return next(self.iter_actor_objects_raw(True))


	def __init__(self, config: Config) -> None:
		self.config = config
		# cache
		self._icons_equipment: IconsEquipment | None = None
		self._icons_npc: UiNpcUnique | None = None
		self._icons_total: UiIconstotal | None = None
		self._maps: Maps | None = None  # game maps (levels)
		self._graph: GameGraph | None = None  # game graph

	# Game Files Paths API

	@property
	def gamedata_path(self) -> Path | None:
		if (game_data := self.fsgame.get('game_data')):
			return Path(game_data)
		return None

	@property
	def savings_path(self) -> Path | None:
		if (game_saves := self.config.fsgame.get('game_saves')):
			return Path(game_saves)
		return None

	@property
	def gamegraph_file_path(self) -> Path | None:
		if (gamedata := self.gamedata_path):
			return gamedata / 'game.graph'
		return None

	# Icons API

	@property
	def icons_equipment(self) -> IconsEquipment:
		'returns icons; it cached'
		if self._icons_equipment:
			return self._icons_equipment
		self._icons_equipment = IconsEquipment(self.config.game_config.paths)
		return self._icons_equipment

	@property
	def icons_npc(self) -> UiNpcUnique:
		'returns icons; it cached'
		if self._icons_npc:
			return self._icons_npc
		self._icons_npc = UiNpcUnique(self.config.game_config.paths)
		return self._icons_npc

	@property
	def icons_npc(self) -> UiIconstotal:
		'returns icons; it cached'
		if self._icons_total:
			return self._icons_total
		self._icons_total = UiIconstotal(self.config.game_config.paths)
		return self._icons_total

	# Maps (levels) API

	@property
	def maps(self) -> Maps:
		'returns maps; it cached'
		if self._maps:
			return self._maps
		self._maps = Maps(self.config.game_config)
		return self._maps

	def get_map_name_by_graph(self, vertex_id: int | None) -> str | None:
		'''returns map (level) name by Game Graph vertex index
		Note: returned map name (Game Graph) may differ from .ltx map name
		'''
		if vertex_id is not None and (gg := self.graph):
			# find game vertex by index
			if (vertex := next(islice(gg.iter_vertexes(), vertex_id, vertex_id + 1))):  # get vertex by index
				if (level := gg.get_level_by_id(vertex[2])):  # get level by id
					return level[0]
		return None

	def get_map_by_graph_map_name(self, map_name: str | None) -> Maps.Map | None:
		'returns .ltx map by Game Graph map (level) name'
		if map_name and (maps := self.maps):
			# try get .ltx map by Game Graph map name; it differ than .ltx map (level) name
			if (map := maps.get_map(map_name)) or (map := maps.get_map('l'+map_name)):
				return map
		return None

	# Localization API

	def localize(self, id: str, html_format = False, localized_only = False) -> str | None:
		'''returns localized text by id with different formats since localized text may have formatting
		id - localized text id
		html_format - convert returned text to html code
		localized_only - returns None (instead id) if localized text not found
		'''
		return self.config.game_config.localize(id, html_format, localized_only)

	def get_localization_lang(self) -> str:
		'returns localization language code: rus, cz, hg, pol e.t.c'
		return self.config.game_config.localization.language

	# Game Graph API

	@property
	def graph(self) -> GameGraph:
		'returns Game Graph; it cached'
		if self._graph:
			return self._graph
		self._graph = GameGraph(self.config.game_config.paths)
		return self._graph

	# .sav files API

	def iter_saved_names(self) -> Iterator[str]:
		'iters game .sav saves names'
		for path in Path(self.savings_path).glob('*.sav'):
			yield path.stem

	def get_save(self, name: str) -> 'Game.Save':
		'''returns Save by game save name: stem of .sav file
		raises SavFileNotFoundError
		'''
		return self.Save(self, name)

	def get_save_file_path(self, save_name: str) -> Path | None:
		'returns .sav file path for save name: all, e.t.c'
		if (save_file_path := Path(self.savings_path) / (save_name+'.sav')) and save_file_path.exists():
			return save_file_path
		return None


if __name__ == '__main__':
	from sys import argv
	import argparse

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray Game:
gamedata: .ltx, .xml localization, items images (icons), maps (levels), game.graph;
runtime: fsgame.ltx, .sav savings

Note:
It is not necessary to extract .db/.xdb files to gamedata path. This utility can read all game files from .db/.xdb files !

Odyssey config example (odyssey.ini):
; Odyssey Game Engine Config
; point format: radius, width, color, outline color
; example: 6, 3, yellow 170, black 180
; color format: named_color; named_color A; R G B; R G B A
; example: yellow 170
; named_color: https://pillow.readthedocs.io/en/stable/reference/ImageColor.html#color-names
[global]
title = S.T.A.L.K.E.R Тень Чернобыля
author = GSC
[odyssey]
path = odyssey
[maps.actor]
point = 6, 3, yellow 170, black 180
''',
				epilog=f'''
Examples:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru s -n all > "SoC.save.all.html
"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', default='.',
				help='game path that contains .db/.xdb files and optional gamedata folder')
			parser.add_argument('--exclude-db-files', metavar='FILE_NAME|PATTERN', nargs='+',
				help='game path that contains .db/.xdb files and optional gamedata folder; Unix shell-style wildcards: *, ?, [seq], [!seq]')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-f', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata directory path; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('--exclude-gamedata', action='store_true', help='exclude files from gamedata sub-path; default: false')
			parser.add_argument('--fsgame', metavar='PATH', default=DEFAULT_FSGAME_FILE_NAME, help=f'fsgame.ltx file path; default: {DEFAULT_FSGAME_FILE_NAME}')
			parser.add_argument('--odyssey', metavar='PATH', default=DEFAULT_ODYSSEY_CONFIG_FILE_NAME, help=f'odyssey.ini file path; default: {DEFAULT_ODYSSEY_CONFIG_FILE_NAME}')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; examples: -v, -vv')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('save', aliases=('s',), help='analyse .sav file')
			parser_.add_argument('-n', '--name', help='.sav file stem')
			parser_.add_argument('-l', '--list', action='store_true', help='list saves names (.sav files stems)')
			return parser.parse_args()


		class LightStyle(NamedTuple):
			page_bgcolor: str = '#e8f1ec'
			bgcolor: str = '#e8f1ec40'
			color: str = 'black'


		class DarkStyle(NamedTuple):
			page_bgcolor: str = '#25252a'
			bgcolor: str = '#20202030'
			color: str = '#c2c7c6'


		class MapPoint(NamedTuple):
			radius: int = 5
			width: int = 1
			color: tuple[int] = (*ImageColor.getrgb('yellow'), 120)
			outline: tuple[int] = (*ImageColor.getrgb('yellow'), 120)


		def point(game: Game, section_name: str, name: str) -> MapPoint:
			if (buff := game.config.odyssey_config.get(section_name, name)):
				buff = buff.split(',', maxsplit=4)
				if len(buff) == 4:
					try:
						return MapPoint(int(buff[0]), int(buff[1]), parse_color(buff[2]), parse_color(buff[3]))
					except ValueError: pass
					print(f'Wrong Map Point format: {", ".join(buff)}')
					return MapPoint()
			return MapPoint()

		def parse_color(buff: str, default: str = 'yellow') -> str:
			try:
				buff = buff.strip().split(' ', maxsplit=4)
				match len(buff):
					case 1:	return ImageColor.getrgb(buff)  # named color
					case 2: return (*ImageColor.getrgb(buff[0]), int(buff[1]))  # named color with alpha
					case 3 | 4: return tuple(map(int, buff))  # RGB/RGBA
				raise ValueError()
			except ValueError:
				print(f'Wrong color format: {buff}')
				return default

		def get_color(game: Game, section_name: str, color_name: str, default: str = 'yellow') -> str:
			buff = game.config.odyssey_config.get(section_name, color_name)
			try:
				return parse_color(buff)
			except ValueError:
				print(f'Wrong color format for {DEFAULT_ODYSSEY_CONFIG_FILE_NAME} [{section_name}]{color_name}: {color}')
				return default

		def create_game() -> Game:
			paths = PathsConfig(args.gamepath, args.version, args.gamedata, exclude_db_files=args.exclude_db_files, verbose=verbose)
			game = Game(Game.Config(GameConfig(paths, localization=args.localization, verbose=verbose),
					odyssey_config_file_name=args.odyssey,
					fsgame_file_name=args.fsgame)
				)
			return game

		def analyse_save(save_name: str, head: str = 'S.T.A.L.K.E.R', style: NamedTuple = DarkStyle):
			print(f'<html>\n<head><title>{head}</title></head>')
			print(f'<body style="background-color:{style.page_bgcolor};color:{style.color};">')
			print(f'<h1>{head}</h1><hr/>')

			if verbose:
				print('<h2>Game log:</h2><pre>')
			game = create_game()
			save = game.get_save(save_name)
			if verbose:
				print(f'Load .sav file: {save.file_path.absolute()}')
				if verbose > 1:
					print('Actor objects:')
					for i, actor_object_raw in enumerate(save.iter_actor_objects_raw()):
						print(i+1, actor_object_raw)
				print('</pre><hr/>')

			print(f'<h2>Save: {save_name}</h2>')

			# show save screenshot image
			if (image := save.screenshot_image):
				image = image.resize((image.width * 4, image.height * 2))
				print('<h3>Screenshot:</h3>')
				print(get_image_as_html_img(image))

			# show save map image, actor condition and suff
			if (map := save.map) and (image := map.image):
				# actor position on map
				print(f'<h3>Map: {map.name+" / " if verbose else ""}{map.localized_name}</h3>')
				if (rect := map.rect) and (actor_object_raw := save.actor_object_raw) and (pos := actor_object_raw.get('position')):
					if verbose:
						print(f'<pre>{rect}</pre>')
					draw = ImageDraw.Draw(image)
					actor_point = point(game, 'maps.actor', 'point')
					draw.circle(map.coord_to_image_point(Pos3d(*pos).pos2d),
				 		actor_point.radius, fill=actor_point.color, outline=actor_point.outline, width=actor_point.width)
				print(get_image_as_html_img(image))

				# actor condition
				if (actor_object_raw := save.actor_object_raw):
					print('<h3>Actor:</h3>')
					if (health := actor_object_raw.get('health')) is not None:
						print(f'<h4>health: {health:.1f}</h4>')
					if (radiation := actor_object_raw.get('radiation')) is not None:
						print(f'<h4>radiation: {radiation:.1f}</h4>')

				# actor stuff
				print('<h3>Stuff:</h3>')
				print('<p>')
				for obj in save.iter_actor_objects():
					if verbose > 1:
						print(f'<pre>{obj.section.name}</pre>')
					print(get_image_as_html_img(obj.image))
				print('</p>')

				if verbose:
					print('</pre><hr/>')
				
			# close html body
			print('</body>\n</html>')

		# read command line arguments
		args = parse_args()
		verbose = args.v

		match args.mode:
			case 'save' | 's':
				if args.list:
					game = create_game()
					for save_name in game.iter_saved_names():
						print(f'{save_name}')
				elif args.name:
					analyse_save(args.name)

		# if (game_saves := Path(game.fsgame.get('game_saves'))) and game_saves.exists():
		# 	for fpath in game_saves.glob('*.sav'):
		# 		analyse_save(fpath)
		
		# try:
		# 	config = WebGame.Config(args.game, fsgame_file_name=args.fsgame)
		# except (WebGame.GamePathNotExistsError, WebGame.GamePathNotValidError):
		# 	exit(-1)
		# except WebGame.FsgameFileNotFoundError:
		# 	exit(-2)
		# except (WebGame.GamedataPathNotExistsError, WebGame.GamedataPathNotValidError):
		# 	exit(-3)

		# game = WebGame(config)
		# if args.debug:
		# 	print('Cache savings')
		# game._savings_cache_timer.start()

		# # show QR code to mobile client to open web page
		# if args.address != '0.0.0.0':  # is IP address defined
		# 	qr = qrcode.QRCode()
		# 	qr.add_data(f'http://{args.address}:{args.port}/')
		# 	qr.print_ascii()

		# # run web server
		# # run(host=args.address, port=args.port, reloader=args.debug, debug=args.debug)
		# t = Thread(target=run, kwargs=dict(host=args.address, port=args.port, reloader=False, debug=args.debug))
		# t.run()
		# if args.debug:
		# 	print('\tWaiting while all threads stopped')
		# try:
		# 	game._savings_cache_timer.stop()
		# except KeyboardInterrupt: pass

	try:
		main()
	except Game.FsgameFileNotFoundError: pass
	except UnspecifiedDbFormat:
		print('UnspecifiedDbFormat. Use -t option')
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
