
# Main class for Stalker Xray and Odyssey game files
# Author: Stalker tools, 2023-2024

from typing import Iterator
from configparser import ConfigParser
from pathlib import Path
from itertools import islice
from PIL.Image import open as image_open, Image
# tools imports
from fsgame import parse as fsgame_parse
from GameConfig import GameConfig, Ltx
from GameGraph import GameGraph
from maps_tool import Maps
from icon_tools import IconsEquipment
from save_tool import Save
from paths import Paths


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
	class GamePathNotExistsError(GameBaseException): pass
	class GamePathNotValidError(GameBaseException): pass
	class GamedataPathNotExistsError(GameBaseException): pass
	class GamedataPathNotValidError(GameBaseException): pass
	class FsgameFileNotFoundError(GameBaseException): pass


	class Config:
		game_path: Path  # game path; path that contains fsgame.ltx file and gamedata folder
		gamedata_path: Path
		title: str  # odyssey title; comes from odyssey.ini
		author: str  # odyssey author; comes from odyssey.ini
		maps: Maps  # game maps .ltx files; loads from gamedata folder
		game_config: GameConfig  # game .ltx files; loads from gamedata folder
		icons: IconsEquipment  # game icons; loads from gamedata folder
		odyssey_path: Path  # odyssey path; path that contains python files and profiles for web interface

		def __init__(self, game_path: str, odyssey_config_file_name: str = DEFAULT_ODYSSEY_CONFIG_FILE_NAME,
			   fsgame_file_name: str = DEFAULT_FSGAME_FILE_NAME,
			   gamedata_path: str | None = DEFAULT_GAMEDATA,
			   localization: str = DEFAULT_LOCALIZATION,
			   debug: bool = False):
			self.debug = debug
			# check game path
			self.game_path = self._check_path(game_path, 'Game', Game.GamePathNotValidError, Game.GamePathNotExistsError)
			self.paths = Paths(self.game_path)
			# load configs
			self._read_odyssey_config(odyssey_config_file_name)  # load odyssey config
			self._ini_python()
			self._read_fsgame(fsgame_file_name)  # load stalker config
			# check gamedata path
			self.gamedata_path = self._check_path(gamedata_path, 'Gamedata',
				Game.GamedataPathNotValidError, Game.GamedataPathNotExistsError, True)
			# load game .ltx files
			if self.debug:
				print('Load game .ltx files and .xml localization')
			self.game_config = GameConfig(str(self.gamedata_path), localization)
			# load game maps
			self._load_maps()
			self.icons = IconsEquipment(self.gamedata_path)

		def _check_path(self, path: str, name: str, not_valid_exeption, not_exists_exeption, game_related = False) -> Path:
			if self.debug:
				print(f'Check {name} path: {path}')
			if not path:
				raise not_valid_exeption(f'{name} path not valid: {path}')
			path = Path(path)
			if game_related and not path.is_absolute():
				path = self.game_path.joinpath(path)
			if not path.exists():
				raise not_exists_exeption(f'{name} path not exists: {path}')
			if not path.is_dir():
				raise not_valid_exeption(f'{name} path is not directory: {path}')
			return path

		def _read_odyssey_config(self, odyssey_config_file_name: str) -> None:
			'reads odyssey.ini file'
			self.odyssey_config_file_path = self.game_path.joinpath(odyssey_config_file_name)
			if self.debug:
				print(f'Read odyssey config file: {self.odyssey_config_file_path}')
			config_parser = self.odyssey
			config_parser.read(self.odyssey_config_file_path)
			self.title = config_parser.get('global', 'title', fallback=None) or DEFAULT_TITLE
			self.author = config_parser.get('global', 'author', fallback=None) or DEFAULT_AUTHOR
			self.odyssey_path = Path(self.game_path).joinpath(
				config_parser.get('global', 'odyssey', fallback=None) or DEFAULT_ODYSSEY_PATH)

		def _ini_python(self):
			self.odyssey_python_root_file_path: Path | None = None
			if (root := self.odyssey.get('game', 'root', fallback=None)):
				self.odyssey_python_root_file_path = self.odyssey_config_file_path.parent.joinpath('odyssey').joinpath(root)

		@property
		def odyssey(self) -> ConfigParser:
			'odyssey config'
			config_parser = ConfigParser()
			config_parser.read(self.odyssey_config_file_path)
			return config_parser

		def _read_fsgame(self, fsgame_file_name: str) -> None:
			'reads fsgame.ltx file'
			fsgame_file_path = self.game_path.joinpath(fsgame_file_name)
			if self.debug:
				print(f'Read fsgame.ltx file: {fsgame_file_path}')
			try:
				self.fsgame = fsgame_parse(fsgame_file_path)
			except FileNotFoundError as e:
				raise self.FsgameFileNotFoundError from e

		def _load_maps(self) -> None:
			'loads game maps from .ltx file'
			if self.debug:
				print('Load game maps .ltx')
			self.maps = Maps(self.paths)
			if self.debug:
				# print maps names
				for i, name in enumerate(self.iter_map_names()):
					print(f'\t{i:02}\t{name}')

		def iter_map_sections(self) -> Iterator[Ltx.Section]:
			'iterates game maps .ltx file sections'
			if self.maps.maps:
				for section in self.maps.maps:
					yield section

		def iter_map_names(self) -> Iterator[str]:
			'iterates game maps names'
			for section in self.iter_map_sections():
				yield section.name


	def __init__(self, config: Config) -> None:
		self.config = config

	@property
	def gamedata_path(self) -> Path | None:
		if (game_data := self.config.fsgame.get('game_data')):
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
			return Path(gamedata).joinpath('game.graph')
		return None

	def iter_sections(self) -> Iterator[Ltx.Section]:
		'iter all loaded .ltx files sections'
		for section in self.config.game_config.iter():
			yield section

	def get_section(self, name: str | None) -> Ltx.Section | None:
		'returns .ltx file section by name'
		if name:
			for section in self.iter_sections():
				if section.name == name:
					return section
		return None

	def localize(self, id: str, html_format = False, localized_only = False) -> str | None:
		'localize from .xml localization file'
		return self.config.game_config.localize(id, html_format, localized_only)

	@classmethod
	def iter_save_actor_objects(cls, save_file_path: str, actor_only = False) -> Iterator[dict]:
		'iterates .sav file for actor object or belongs to actor objects'
		gs = Save(save_file_path)
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

	@classmethod
	def has_save_actor_object(cls, save_file_path: str, name: str) -> bool:
		return any((x for x in cls.iter_save_actor_objects(save_file_path) if x.get('name') == name))

	def get_map_img_file_path(self, map_name: str) -> str | None:
		'returns map image file path by name: global e.t.c.'
		if self.config.maps:
			if map_name =='global':
				if (image := self.config.maps.get_image_file_path(self.config.maps.global_map)):
					return image
			elif (section := next((x for x in self.config.maps.maps if x.name == map_name), None)):
				if (image := self.config.maps.get_image_file_path(section)):
					return image
		return None

	def get_map_img(self, map_name: str) -> Image | None:
		'returns map image by name: global e.t.c.'
		if (level_img_file_path := self.get_map_img_file_path(map_name)):
			return image_open(level_img_file_path)
		return None

	def get_map_name_by_graph(self, vertex_id: int | None) -> str | None:
		'returns map name by graph vertex index'
		if not vertex_id is None and (gg := GameGraph(self.gamegraph_file_path)):
			# find game vertex by index
			if (vertex := next(islice(gg.iter_vertexes(), vertex_id, vertex_id + 1))):  # get vertex by index
				if (level := gg.get_level_by_id(vertex[2])):  # get level by id
					return level[0]
		return None
