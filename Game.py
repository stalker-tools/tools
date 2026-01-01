
# Main class for Stalker Xray and Odyssey game files
# Author: Stalker tools, 2023-2024

from typing import Iterator, NamedTuple, Self
from configparser import ConfigParser
from pathlib import Path
from itertools import islice
from PIL import ImageDraw
from PIL.Image import open as image_open, Image
# tools imports
from fsgame import parse as fsgame_parse
from GameConfig import GameConfig, Ltx
from GameGraph import GameGraph
from maps_tool import Maps, Pos3d
from icon_tools import IconsEquipment, get_image_as_html_img
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
	class SaveFileNotFoundError(GameBaseException): pass


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
				self.odyssey_python_root_file_path = self.odyssey_config_file_path.parent / 'odyssey' /  root

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


	class Save:


		class Object:
			'Save Object'

			def __init__(self, save: 'Game.Save', icons: IconsEquipment, raw_object: dict[str, any], section: Ltx.Section):
				self.save = save
				self.icons = icons
				self.raw_object = raw_object
				self.section = section

			@property
			def image(self) -> Image:
				'returns icon'
				return self.icons.get_image(
					int(self.section.get('inv_grid_x')), int(self.section.get('inv_grid_y')),
					int(self.section.get('inv_grid_width', 1)), int(self.section.get('inv_grid_height', 1)))

			@property
			def pos(self) -> Pos3d | None:
				'returns "position"'
				if (position := self.raw_object.get('position')):
					return Pos3d(position)
				return None


		def __init__(self, game: 'Game', name: str):
			self.game: Game = game
			self.name = name
			self._maps: Maps | None = None
			self.file_path: Path | None = self.game.get_save_file_path(self.name)
			if self.file_path is None:
				raise Game.SaveFileNotFoundError()

		@property
		def screenshot_image(self) -> Image | None:
			if (save_file_path := self.file_path):
				return image_open(save_file_path.with_suffix('.dds'))
			return None

		@property
		def map(self) -> Maps.Map | None:
			'returns Map class for map (level) name (from Game Graph)'
			if (save_file_path := self.game.get_save_file_path(self.name)):
				if (actor := next(self.game.iter_save_actor_objects(save_file_path, True))):
					if (graph_id := actor.get('graph_id')) is not None:
						if (level_name := self.game.get_map_name_by_graph(graph_id)):
							if not self._maps:
								self._maps = self.game.maps
							if (maps := self._maps):
								if (map := maps.get_map(level_name)) or (map := maps.get_map('l'+level_name)):
									return map
			return None

		def iter_actor_objects_raw(self, actor_only = False) -> Iterator[dict]:
			'iterates .sav file for actor object or belongs to actor objects'
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
			icons = IconsEquipment(self.game.config.paths)
			for raw_object in self.iter_actor_objects_raw():
				if raw_object.get('name') != 'actor' and (section := self.game.get_section(raw_object.get('name'))):
					yield self.Object(self, icons, raw_object, section)

		@property
		def actor_object_raw(self) -> dict[str, any]:
			return next(self.iter_actor_objects_raw(True))


	def __init__(self, config: GameConfig, fsgame_file_path: str) -> None:
		self.config = config
		self.fsgame_file_path = Path(fsgame_file_path)  # fsgame.ltx
		if not self.fsgame_file_path.is_absolute():
			self.fsgame_file_path = self.config.paths.path / self.fsgame_file_path
		self._read_fsgame()

	def _read_fsgame(self) -> None:
		'reads fsgame.ltx file'
		if self.config.verbose:
			print(f'Read fsgame.ltx file: {self.fsgame_file_path}')
		try:
			self.fsgame = fsgame_parse(self.fsgame_file_path)
		except FileNotFoundError as e:
			raise self.FsgameFileNotFoundError from e

	# Game Files Paths API

	@property
	def gamedata_path(self) -> Path | None:
		if (game_data := self.fsgame.get('game_data')):
			return Path(game_data)
		return None

	@property
	def savings_path(self) -> Path | None:
		if (game_saves := self.fsgame.get('game_saves')):
			return Path(game_saves)
		return None

	@property
	def gamegraph_file_path(self) -> Path | None:
		if (gamedata := self.gamedata_path):
			return gamedata / 'game.graph'
		return None

	# Maps (levels) API

	@property
	def maps(self) -> Maps:
		'returns maps holder class'
		return Maps(self.config.paths, self.config.localization)

	def get_map_name_by_graph(self, vertex_id: int | None) -> str | None:
		'''returns map (level) name by graph vertex index
		Note: returned map name may differ from .ltx map name
		'''
		if vertex_id is not None and (gg := self.graph):
			# find game vertex by index
			if (vertex := next(islice(gg.iter_vertexes(), vertex_id, vertex_id + 1))):  # get vertex by index
				if (level := gg.get_level_by_id(vertex[2])):  # get level by id
					return level[0]
		return None

	# .ltx Sections API

	def iter_sections(self) -> Iterator[Ltx.Section]:
		'iter all loaded .ltx files sections'
		ltx = Ltx(self.config.paths.system_ltx, open_fn=self.config.paths.open)
		for section in ltx.iter_sections():
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

	# Game Graph API

	@property
	def graph(self) -> GameGraph:
		return GameGraph(self.gamegraph_file_path)

	# .sav files API

	def iter_saves_names(self) -> Iterator[str]:
		for path in Path(self.savings_path).glob('*.sav'):
			yield path.stem

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

	def get_save(self, name: str) -> 'Game.Save':
		'''returns Save class by save name: stem of .sav file
		raises SaveFileNotFoundError
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
''',
				epilog=f'''
Examples:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru s -n all > "SoC.saves.html
"''',
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
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; examples: -v, -vv')
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


		def create_game() -> Game:
			paths = PathsConfig(args.gamepath, args.version, args.gamedata, exclude_db_files=args.exclude_db_files, verbose=verbose)
			game = Game(
				GameConfig(paths,
					localization=args.localization, verbose=verbose),
					args.fsgame
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
				print(f'Save file: {save.file_path.absolute()}')
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

			# show save map image
			if (map := save.map) and (image := map.image):
				print(f'<h3>Map {map.name+" / " if verbose else ""}{map.localized_name}:</h3>')
				if (rect := map.rect) and (actor_object_raw := save.actor_object_raw) and (pos := actor_object_raw.get('position')):
					if verbose:
						print(f'<pre>{rect}</pre>')
					draw = ImageDraw.Draw(image)
					draw.circle(map.coord_to_image_point(Pos3d(*pos).pos2d), 5, fill='yellow', outline='brown')
				print(get_image_as_html_img(image))

				print('<h3>Stuff:</h3>')
				print('<p>')
				for obj in save.iter_actor_objects():
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
					for save_name in game.iter_saves_names():
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
