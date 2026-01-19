#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Main class for Stalker X-ray and Odyssey game files
# It have command-line interface
# Author: Stalker tools, 2023-2026

from typing import Iterator, NamedTuple
from types import ModuleType
from struct import unpack
from configparser import ConfigParser, NoOptionError, NoSectionError
from pathlib import Path
from itertools import islice
from sys import path as sys_path
from PIL import ImageDraw, ImageColor, ImageFont
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
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from DBReader import UnspecifiedDbFormat
from ltx_tool import Ltx


DEFAULT_TITLE = 'Stalker'
DEFAULT_AUTHOR = 'stalker-tools'
DEFAULT_LOCALIZATION = 'ru'
DEFAULT_FSGAME_FILE_NAME = 'fsgame.ltx'
DEFAULT_GAMEDATA = 'gamedata'
DEFAULT_ODYSSEY_CONFIG_FILE_NAME = 'odyssey.ini'
DEFAULT_ODYSSEY_PATH = 'odyssey'


class Events:


	class MapLoad(NamedTuple):
		name: str  # .ltx map (level) name
		localized_name: str
		source: object | None


	class RunOrPause(NamedTuple):
		run: bool  # True: run; False: pause
		source: object | None


class Game:
	'''
	X-ray game config: .ltx, .xml localization, items images (icons), maps (levels), game.graph
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

		__slots__ = ('game', 'name', 'file_path', '_save')

		class Object:
			'Save .sav file object from ObjectChunk'

			__slots__ = ('save', 'raw_object', 'section')


			class Weapon(NamedTuple):
				'weapon data holder from .sav object that belongs to actor'
				condition: float | None = None
				loaded: int | None = None


			class Outfit(NamedTuple):
				'outfit data holder from .sav object that belongs to actor'
				condition: float | None = None


			def __init__(self, save: 'Game.Save', raw_object: dict[str, any], section: Ltx.Section):
				self.save = save
				self.raw_object = raw_object
				self.section = section

			@property
			def ltx_class(self) -> str:
				'returns .ltx section class'
				return self.section.get('class', default_value='')

			@property
			def ltx_name(self) -> str:
				'returns .ltx section name'
				return self.section.name or ''

			@property
			def elapsed(self) -> int | None:
				'used for ammo'
				return self.raw_object.get('elapsed')

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
				'returns "position" on the map (level)'
				if (position := self.raw_object.get('position')):
					return Pos3d(position)
				return None

			@property
			def item_type(self) -> str:
				'returns str for object as type-specific characteristic'
				return self.ltx_class.partition('_')[0]  # prefix of .ltx class

			def get_actor_object_data(self) -> Weapon | Outfit | None:
				'returns specific extracted data from .sav object'
				if (client_data := self.raw_object.get('client_data')):
					if (ltx_class := self.section.section.get('class')) and ltx_class.startswith('WP_'):
						return self.Weapon(
							unpack('f', client_data[2:6])[0],
							unpack('H', client_data[7:9])[0],
							)
					elif (ltx_class := self.section.section.get('class')) and ltx_class.startswith('E_STLK'):
						return self.Outfit(
							unpack('f', client_data[2:6])[0],
							)
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
			self._save: Save | None = None  # cache

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
			if not self._save:
				self._save = Save(self.file_path)  # Game Save
			for chunk in self._save.iter_chunks():
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


	def __init__(self, config: Config, load_addons: bool = False) -> None:
		self.config = config
		# cache
		self._icons_equipment: IconsEquipment | None = None
		self._icons_npc: UiNpcUnique | None = None
		self._icons_total: UiIconstotal | None = None
		self._maps: Maps | None = None  # game maps (levels)
		self._graph: GameGraph | None = None  # game graph
		self.addons: dict[str, object] = {}
		if load_addons:
			self._load_addons()

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

	# Addons API

	def _load_addons(self):
		if (addons_path := Settings.Odyssey.get_path(self)) and addons_path.exists():
			if self.config.game_config.verbose > 1:
				print(f'Add addon path to Python: {addons_path.absolute()}')
			sys_path.insert(0, str(addons_path.absolute()))
			for p in Settings.Odyssey.iter_addons_paths(self):
				if self.config.game_config.verbose:
					print(f'Load addon: {p.absolute()}')
				addon = __import__(p.stem)
				if not hasattr(addon, 'ADDONS'):
					print(f'Wrong addon: {p.absolute()}')
					continue
				for addon in addon.ADDONS:
					self.addons[p.stem] = addon(self)

	def event_sink(self, event: Events.MapLoad | Events.RunOrPause) -> None:
		for addon in self.addons.values():
			addon.event(event)

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


class Settings:
	'settings from odyssey.ini'

	@classmethod
	def get_option(cls, game: Game, section: str, option: str, default: str) -> str:
		'returns settings option'
		# read from odyssey.ini
		try:
			if (buff := game.config.odyssey_config.get(section, option)):
				return buff
		except (NoSectionError, NoOptionError): pass
		return default


	class Global:
		'reads global settings from Odyssey Config: odyssey.ini'

		SECTION = 'global'
		TITLE_OPTION = 'title'
		AUTHOR_OPTION = 'author'
		DEFAULT_TITLE = 'S.T.A.L.K.E.R'
		DEFAULT_AUTHOR = 'GSC'

		@classmethod
		def get_title(cls, game: Game) -> str:
			'returns title'
			# read from odyssey.ini
			return Settings.get_option(game, cls.SECTION, cls.TITLE_OPTION, cls.DEFAULT_TITLE)

		@classmethod
		def get_author(cls, game: Game) -> str:
			'returns author'
			# read from odyssey.ini
			return Settings.get_option(game, cls.SECTION, cls.AUTHOR_OPTION, cls.DEFAULT_AUTHOR)


	class Html:
		'reads html settings from Odyssey Config: odyssey.ini'

		SECTION = 'html'
		STYLE_OPTION = 'style'
		DEFAULT_STYLE = 'dark'


		class LightStyle(NamedTuple):
			page_bgcolor: str = '#e8f1ec'
			bgcolor: str = '#e8f1ec40'
			color: str = 'black'


		class DarkStyle(NamedTuple):
			page_bgcolor: str = '#25252a'
			bgcolor: str = '#20202030'
			color: str = '#c2c7c6'


		STYLE_NAMES = {
			'dark': DarkStyle,
			'd': DarkStyle,
			'light': LightStyle,
			'l': LightStyle,
		}

		@classmethod
		def get_style(cls, game_or_style: Game | str | None) -> DarkStyle | LightStyle:
			'returns style or default style'
			if game_or_style is None:
				return cls.STYLE_NAMES[cls.DEFAULT_STYLE]
			if isinstance(game_or_style, str):
				return cls.STYLE_NAMES.get(game_or_style.lower(), cls.STYLE_NAMES[cls.DEFAULT_STYLE])
			# read from odyssey.ini
			return cls.STYLE_NAMES[Settings.get_option(game_or_style, cls.SECTION, cls.STYLE_OPTION, cls.DEFAULT_STYLE)]


	class MapImage:
		'reads map (level) image settings from Odyssey Config: odyssey.ini'

		DEFAULT_COLOR = 'yellow'

		# .ini section/option names
		ACTOR_POINT_SECTION = 'maps.actor'
		ACTOR_POINT_OPTION = 'point'
		ACTOR_TEXT_OPTION = 'text'

		@classmethod
		def get_actor_point(cls, game: Game) -> 'Point | None':
			try:
				return cls.Point.from_config(game, cls.ACTOR_POINT_SECTION, cls.ACTOR_POINT_OPTION)
			except (NoSectionError, NoOptionError): return cls.Point()

		@classmethod
		def get_actor_text(cls, game: Game) -> 'Point | None':
			try:
				return cls.TextPoint.from_config(game, cls.ACTOR_POINT_SECTION, cls.ACTOR_TEXT_OPTION)
			except (NoSectionError, NoOptionError): return None

		@classmethod
		def parse_color(cls, buff: str, default: str = DEFAULT_COLOR) -> str:
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

		@classmethod
		def get_color(cls, game: Game, section_name: str, color_name: str, default: str = DEFAULT_COLOR) -> str:
			return cls.parse_color(game.config.odyssey_config.get(section_name, color_name), default)


		class Point(NamedTuple):
			radius: int = 7
			width: int = 3
			color: tuple[int] = (*ImageColor.getrgb('yellow'), 170)
			outline: tuple[int] = (*ImageColor.getrgb('black'), 150)

			@classmethod
			def from_config(cls, game: Game, section_name: str, name: str) -> 'Point':
				if (buff := game.config.odyssey_config.get(section_name, name)):
					buff = buff.split(',', maxsplit=4)
					if len(buff) == 4:
						try:
							return cls(int(buff[0]), int(buff[1]),
								Settings.MapImage.parse_color(buff[2]), Settings.MapImage.parse_color(buff[3]))
						except ValueError: pass
						print(f'Wrong Map Point format: {", ".join(buff)}')
				return cls()


		class TextPoint(NamedTuple):
			text: str = '🗶'
			size: int = 48
			color: tuple[int] = (*ImageColor.getrgb('yellow'), 120)
			font: str = Paths.convert_path_to_os('web/Symbola.ttf')

			@classmethod
			def from_config(cls, game: Game, section_name: str, name: str) -> 'TextPoint':
				if (buff := game.config.odyssey_config.get(section_name, name)):
					buff = buff.split(',', maxsplit=3)
					try:
						match len(buff):
							# "", size, color
							case 3: return cls(buff[0], int(buff[1]), Settings.MapImage.parse_color(buff[2]))
							# "", size, color, font file path
							case 4: return cls(buff[0], int(buff[1]), Settings.MapImage.parse_color(buff[2]),
								Paths.convert_path_to_os(buff[3]))
					except ValueError: pass
					print(f'Wrong Text Point format: {", ".join(buff)}')
				return cls()


	class Odyssey:
		'reads odyssey settings from Odyssey Config: odyssey.ini'

		SECTION = 'odyssey'
		PATH_OPTION = 'path'
		DEFAULT_PATH = 'odyssey'

		@classmethod
		def get_path(cls, game: Game) -> Path:
			'returns path'
			# read from odyssey.ini
			addons_path = Path(Settings.get_option(game, cls.SECTION, cls.PATH_OPTION, cls.DEFAULT_PATH))
			if not addons_path.is_absolute():
				addons_path = game.config.game_config.paths.path / addons_path
			return addons_path

		@classmethod
		def iter_addons_paths(cls, game: Game) -> Iterator[Path]:
			addons_path = Path(cls.get_path(game))
			for p in (x for x in addons_path.iterdir() if x.is_file() and x.suffix == '.py'):
				yield p


if __name__ == '__main__':
	from sys import argv
	import argparse
	from struct import unpack

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

		def create_game(load_addons: bool = False) -> Game:
			paths = PathsConfig(args.gamepath, args.version, args.gamedata, exclude_db_files=args.exclude_db_files, verbose=verbose)
			game = Game(Game.Config(GameConfig(paths, localization=args.localization, verbose=verbose),
				odyssey_config_file_name=args.odyssey,
				fsgame_file_name=args.fsgame),
				load_addons,
				)
			return game

		def analyse_save(save_name: str, head: str = 'S.T.A.L.K.E.R', style: str | None = None):

			# define html style
			style = Settings.Html.get_style(style)

			print(f'<html>\n<head><title>{head}</title></head>')
			print(f'<body style="background-color:{style.page_bgcolor};color:{style.color};">')

			if verbose:
				print('<h2>Game log:</h2><pre>')
			game = create_game(load_addons=True)
			save = game.get_save(save_name)  # get .sav file
			if verbose:
				print(f'Load .sav file: {save.file_path.absolute()}')
				if verbose > 1:
					print('Actor objects:')
					for i, actor_object_raw in enumerate(save.iter_actor_objects_raw()):
						print(i+1, actor_object_raw)
				print('</pre><hr/>')

			print(f'<h1>{Settings.Global.get_title(game)}</h1><hr/>')
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
					# point
					if (actor_point := Settings.MapImage.get_actor_point(game)):
						draw.circle(map.coord_to_image_point(Pos3d(*pos).pos2d),
							actor_point.radius, fill=actor_point.color, outline=actor_point.outline, width=actor_point.width)
					# text
					if (actor_text := Settings.MapImage.get_actor_text(game)):
						draw.text(map.coord_to_image_point(Pos3d(*pos).pos2d), actor_text.text, actor_text.color,
							align='center', anchor='mm', font=ImageFont.truetype(actor_text.font, actor_text.size))
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
			# group stuff by .ltx sections and count
			obj_count: dict[str, int] = {}
			for obj in save.iter_actor_objects():
				obj_count[obj.ltx_name] = obj_count.get(obj.ltx_name, 0) + (obj.elapsed or 1)
			# sort by .ltx class
			prev_type, prev_section_name, count = None, None, None
			# sort by class and name since multiple items may share one class
			# show actor items (objects) grouped by kind
			for obj in sorted(save.iter_actor_objects(), key=lambda x: x.ltx_class+x.ltx_name):
				if obj.ltx_name not in obj_count:
					if prev_section_name:
						# show repeated item as group
						if (data := obj.get_actor_object_data()):
							match type(data):
								case obj.Weapon:
									print(f'<td style="vertical-align: bottom; height: 100%; padding: 0; border: 1px solid; "><div style="height: {data.condition:.0%};width: min-content; border-top: 2px solid;"><sub>{data.loaded}</sub></div>')
								case obj.Outfit:
									print(f'<td style="vertical-align: bottom; height: 100%; padding: 0; border: 1px solid; "><div style="height: {data.condition:.0%};width: min-content; border-top: 2px solid;">&nbsp;</div>')
					continue  # skip repeated items
				if prev_section_name:
					prev_section_name = None
					# close group block for multiple items of the same type
					print('</tr></table>')
					print('<div style="display: table;text-align: center;padding-bottom: 3px;border-bottom: 1px solid;border-bottom-left-radius: 12px;">')
					print(count)
					print('</div></div>')
				if prev_type is None:
					prev_type = obj.item_type
				elif prev_type != obj.item_type:
					prev_type = obj.item_type
					print('<br/>')  # start new line: new group
				print('<div style="display: inline grid;padding-left: 5px;padding-bottom: 5px;">')
				if verbose > 1:
					print(f'<pre>{obj.ltx_name}</pre>')
				count = obj_count[obj.ltx_name]
				# show item-type specific info
				print('<table><tr><td>')
				print(get_image_as_html_img(obj.image))
				print('</td>')
				if obj.elapsed:
					# ammo
					print('</td></table>')
					print(f'<div style="display: table;text-align: center;padding-bottom: 3px;border-bottom: 1px solid;border-bottom-left-radius: 12px;"><sub>{count}</sub></div></div>')
				else:
					if (data := obj.get_actor_object_data()):
						match type(data):  # check for specific .sav object data
							case obj.Weapon:
								print(f'<td style="vertical-align: bottom; height: 100%; padding: 0; border: 1px solid; "><div style="height: {data.condition:.0%};width: min-content; border-top: 2px solid;"><sub>{data.loaded}</sub></div></td>')
								if count > 1:
									# show next items as group
									prev_section_name = obj.ltx_name
								else:
									print('</tr></table></div>')
							case obj.Outfit:
								print(f'<td style="vertical-align: bottom; height: 100%; padding: 0; border: 1px solid; "><div style="height: {data.condition:.0%};width: min-content; border-top: 2px solid;">&nbsp;</div></td>')
								if count > 1:
									# show next items as group
									prev_section_name = obj.ltx_name
								else:
									print('</tr></table></div>')
							case _:  # regular
								print('</td></table></div>')
					else:  # regular
						print('</td></table></div>')
				if (count := obj_count[obj.ltx_name]) > 1:
					del obj_count[obj.ltx_name]
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
