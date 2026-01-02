
# Odyssey/Stalker Xray game file paths tool for mixed filesystems: filesystem (gamedata) and .db/.xdb files
# Used to work with gamedata files from two media sources that shares one logical files paths tree:
# - .db/.xdb files;
# - gamedata folder.
# Note: it ready-to-use with pypy: pypy3.11-7.3.20 tested
# Author: Stalker tools, 2023-2025

from typing import Iterable, Self, Generator, Iterator
from os.path import join, abspath, sep
from pathlib import Path
from contextlib import contextmanager
from codecs import getreader, StreamReader
from io import UnsupportedOperation
from fnmatch import fnmatch
from pickle import load as pickle_load, dump as pickle_dump
# tools imports
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from LayeredFileSystem import LayeredFileSystem, PathType, LayerBase, FileIoBase
from DBReader import XRReader, DbFileVersion, ChunkTypes, WrongDbFormat, UnspecifiedDbFormat


DEFAULT_GAMEDATA_PATH = 'gamedata'
DEFAULT_OS_ENCODING = 'utf-8'
DEFAULT_GAME_ENCODING = 'cp1251'
TEXT_FILES_EXT = ('.ltx', '.xml', '.script')
DEFAULT_GAME_LENESEP_B = b'\r\n'

def is_xml_utf_8_file(path: str, buff: bytes | None = None) -> bool:
	# little hack for .xml files; todo: use BOM to detect binary UTF format
	if buff and path.endswith('.xml') and b'UTF-8' in buff:
		return True  # buff has utf-8 encoding - use it as binary
	return False

def is_text_file(path: str, buff: bytes | None = None) -> bool:
	'''defines is text file or binary file by file extension
	Note: .xml has special behaviour but it requires binary buffer
	'''
	for ext in TEXT_FILES_EXT:
		if path.endswith(ext):
			# little hack for .xml files; todo: use BOM to detect binary UTF format
			if buff and is_xml_utf_8_file(path, buff):
				return False  # buff has utf-8 encoding - use it as binary
			return True
	return False


class Config:
	'Game Paths config'

	def __init__(self, game_path: str, version: str | None = None, gamedata_path: str = DEFAULT_GAMEDATA_PATH,
			exclude_db_files: list[str] | None = None, verbose: int = 0, exclude_gamedata: bool = False):
		self.game_path = game_path
		self.gamedata_path = gamedata_path
		self.version = version
		self.exclude_db_files = exclude_db_files
		self.verbose = verbose
		self.is_gamedata_exclude = exclude_gamedata
	def __repr__(self):
		return f'game_path="{self.game_path}" gamedata_path="{self.gamedata_path}" version={self.version} exclude_db_files={self.exclude_db_files} is_gamedata_exclude={self.is_gamedata_exclude}'


class Paths:
	'main class that manages game paths'

	SEP = '\\'  # path parts separator for Xray

	def __init__(self, gamedata_path: str | Self | Config) -> None:
		if isinstance(gamedata_path, Paths):
			self = gamedata_path
			return

		# load .db/.xdb files
		self.config = None
		self.gamedata_db_files: dict[str, str] | None = None  # {gamedata: .db/.xdb} gamedata .db/.xdb files
		self.db_gamedata_files: dict[str, list[str]] | None = None  # {.db/.xdb: gamedata} .db/.xdb gamedata files
		if isinstance(gamedata_path, Config):
			self.config = gamedata_path
			# define well-known root sub-paths
			self.path = Path(self.config.game_path).resolve()  # root game path: .db/.xdb files and optionally gamedata folder
			self.cache_path = self.path / 'cache'
			if self.path.exists() and not self.cache_path.exists():
				self.cache_path.mkdir(parents=True)
			# resolve gamedata path: it can be absolute or relative to game root
			self.gamedata = Path(self.config.gamedata_path)
			if not self.gamedata.is_absolute():  # is gamedata relative to game root path
				self.gamedata = (self.path / self.gamedata).resolve()
			else:
				self.gamedata.resolve()
			if self.config.verbose:
				print(f'game path:     {self.path.absolute()}')
				print(f'gamedata path: {self.gamedata.absolute()}')
			# load .db/.xdb files
			self.gamedata_db_files = self._init_latest_db_gamedata_files(self.config)
			self.db_gamedata_files = {}
			for ff, f in self.gamedata_db_files.items():
				if f in self.db_gamedata_files:
					self.db_gamedata_files[f].append(ff)
				else:
					self.db_gamedata_files[f] = [ff]
			self.db_gamedata_files
		else:
			# define well-known root sub-paths
			self.gamedata = Path(gamedata_path)
			self.path = self.gamedata.parent
			if self.config.verbose:
				print(f'game path:     {self.path.absolute()}')
				print(f'gamedata path: {self.gamedata.absolute()}')

		# init layered file system for gamedata files: .db/.xdb files, OS gamedata path
		# layers order is matter: first - OS gamedata path, then - .db/.xdb files
		fs_layers = []
		if not self.config.is_gamedata_exclude:
			fs_layers.append(OsGamedataFs(self))
		if self.gamedata_db_files:
			fs_layers.append(DbGamedataFs(self))
		self.layered_fs = LayeredFileSystem(fs_layers)

		# define well-known sub-paths

		# configs sub-path is version-dependent: .ltx files, gameplay/UI/dialogs .xml files
		if self.exists('config', False):
			self.configs = 'config'  # SoC
		elif self.exists('configs', False):
			self.configs = 'configs'
		else:
			raise FileNotFoundError(f'Stalker configs path not found: {self.gamedata}')

	def __str__(self) -> str:
		return f'Paths({self.gamedata})'

	@classmethod
	def _init_latest_db_gamedata_files(cls, config: Config) -> dict[str, str]:
		''' loads all .db/.xdb files and defines latest version of gamedata files

		game_path: root game path: search path for .db/.xdb files
		version: .db/.xdb files version: usually 2947ru/2947ww for SoC, xdb for CS and CP
		exclude_db_files: filter for .db/.xdb files names: Unix shell pattern
		verbose: verbose level: 0..
		
		returns dict {gamedata path/file name: .db/.xdb file name}
		'''

		def get_cache_file_path() -> Path:
			return Path(config.game_path) / 'cache' / 'gamedata.cache'

		def iter_db_files() -> Iterator[Path]:
			'iters .db/.xdb files in game path'

			def is_db_file_skipped(db_path: str) -> bool:
				# check for exclude files as Unix shell pattern
				if config.exclude_db_files:
					for exclude_db_file in config.exclude_db_files:
						if '*' in exclude_db_file or '?' in exclude_db_file or '[' in exclude_db_file:
							# filter is pattern
							if fnmatch(db_path, exclude_db_file):
								return True  # exclude file
						elif exclude_db_file == db_path:  # filter is not pattern
							return True  # exclude file
				return False

			for f in sorted(Path(x) for x in Path(config.game_path).glob('gamedata.*db?') if x.is_file()):
				# check for exclude files as Unix shell pattern
				if not is_db_file_skipped(f.name):
					yield f

		if get_cache_file_path().exists():
			# load from cache
			if config.verbose:
				print(f'Load .db/.xdb from cache: {get_cache_file_path()}')
			with open(get_cache_file_path(), 'rb') as f_cache:
				try:
					config_cached, files_cached = pickle_load(f_cache)
					if config.exclude_db_files == config_cached.exclude_db_files:
						return files_cached
				except (TypeError, EOFError): pass

		# get latest gamedata files version # read all .db/.xdb files and fill dict {file: .db/.xdb file}
		files: dict[str, str] = {}  # gamedata file path: .db file name
		for i, f in enumerate(iter_db_files()):
			if config.verbose:
				print(f'Load .db/.xdb file {i + 1:2}: {f.name}')
			db_reader = XRReader(f, config.version)
			for ff in db_reader.iter_files():
				files[ff.name] = f.name
		files = dict(sorted(files.items(), key=lambda x: x[0]))  # sort by gamedata file path

		# update cache
		with open(get_cache_file_path(), 'wb') as f_cache:
			pickle_dump((config, files), f_cache)

		return files

	def exists(self, path: str, file_wanted: bool = True) -> PathType:
		return self.layered_fs.exists(path, file_wanted)

	@contextmanager
	def open(self, path: str, mode: str = 'r') -> Generator[FileIoBase | StreamReader, None, None]:
		# print(f'OPEN {mode=} {path=}')
		if path is None:
			raise ValueError('opne path is None')
		if self.config.verbose > 2:
			print(f'Open {path=} {mode=}')
		if (f := self.layered_fs.open(path, mode)):
			if self.config.verbose > 2:
				print(f'\t{f=}')
			try:
				text_reader = None
				if not 'b' in mode:
					# text mode # add text reader with game encoding
					text_reader = getreader(DEFAULT_GAME_ENCODING)(f)
					yield text_reader
				else:
					yield f
			finally:
				# print(f'EXIT: {path=}')
				del text_reader
				del f
		else:
			raise FileNotFoundError(f'File not found: {path}')

	# Well-known paths

	@property
	def game(self) -> str:
		'returns game root path'
		return abspath(join(self.gamedata, '..'))

	@property
	def system_ltx(self) -> str:
		'returns system.ltx file path'
		return join(self.configs, 'system.ltx')

	@property
	def game_ltx(self) -> str:
		'returns game.ltx file path'
		return join(self.configs, 'game.ltx')

	@property
	def game_graph(self) -> str:
		'returns game.graph file path'
		return 'game.graph'

	# helper functions

	def find(self, pattern: str) -> Iterator[str]:
		'iters gamedata files paths according to Unix shell-style wildcards: *, ?, [seq], [!seq]'
		for ff, _ in self.gamedata_db_files.items():
			if fnmatch(ff, pattern):
				yield ff

	@classmethod
	def join(cls, *paths: Iterable[str]) -> str:
		'cross-platform path join'
		if cls.SEP == sep:
			return join(*paths)
		return join(*(x.replace('\\', sep) for x in paths))

	@classmethod
	def convert_path_to_os(cls, path: str) -> str:
		if cls.SEP == sep:
			return path
		return path.replace(cls.SEP, sep)

	def relative(self, path: str) -> str:
		'return relative path to gamedata'
		p = Path(path)
		if not p.is_relative_to(self.gamedata):
			return path
		return str(p.relative_to(self.gamedata))

	def ui_textures_descr(self, common_name: str) -> str:
		'return UI textures .xml file path: <gamedata path>/configs/ui/textures_descr/.xml'
		if self.configs == 'config':
			return join(self.configs, 'ui', f'{common_name}.xml')
		return join(self.configs, 'ui', 'textures_descr', f'{common_name}.xml')

	def ui_textures(self, common_name: str) -> str:
		'return UI textures .dds file path: <gamedata path>/textures/ui/.dds'
		return join('textures', 'ui', f'{common_name}.dds')


# Layers for LayeredFileSystem

class DbFileIo(FileIoBase):
	'.db/.xdb files I/O object; used for read latest file fersion from .db/.xdb file'

	def __init__(self, path: str, db_path: str, db_version: str):
		self.path = path  # gamedata file path
		self.db_path = db_path  # .db/.xdb file path
		self.db_version = db_version  # .db/.xdb file version
		self.pos: int = 0  # used for sequential reading

	def _get_db_file(self) -> None | tuple[XRReader, XRReader.FileOrPath]:
		'returns (.db/.xdb file reader, .db/.xdb gamedata file)'
		db_reader = XRReader(self.db_path, self.db_version)  # open .db/.xdb file
		for ff in db_reader.iter_files():  # find gamedata file by path
			if ff.name == self.path:
				return (db_reader, ff)  # file path found
		return None  # file path not found

	def read(self, size=-1) -> bytes | None:
		# check size
		if not isinstance(size, int):
			raise ValueError(f'size has incorrect type: {type(size)}; expected: int')
		if not size:
			return None

		# read latest file fersion from .db/.xdb file
		if (ff := self._get_db_file()):
			db_reader, ff = ff

			# check file
			if ff.size is None:
				raise UnsupportedOperation('.db/.xdb file cannot be read; maybe wrong .db/.xdb file parser implementation')
			if self.pos >= ff.size:
				return b''

			# get file data
			buff = ff.get_data(db_reader)
			if size < 0:
				# read all bytes
				self.pos = ff.size
				return buff
			self.pos = min(self.pos + size, ff.size)
			return buff

		return None

	def readall(self) -> bytes | None:
		return self.read()

	def readlines(self) -> Iterable[str]:
		if (buff := self.read()):
			return buff.splitlines()
		return tuple()

	def write(self, data: bytes) -> int:
		raise UnsupportedOperation('cannot write to .db/.xdb, it read-only filesystem')


class DbGamedataFs(LayerBase):
	'.db/.xdb files filesystem; used for read latest gamedata files fersion from .db/.xdb files'


	class DbFilesIsReadOnlyFs(Exception): pass


	def __init__(self, paths: Paths):
		super().__init__()
		self.paths: Paths = paths

	@classmethod
	def normalize_path(cls, path: str) -> str:
		return path.replace('/', Paths.SEP)  # convert to .db/.xdb gamegata paths

	def _find(self, path: str, file_wanted: bool = True) -> tuple[PathType, str, str] | None:
		'''finds file in all .db/.xdb files
		returns (type, gamedata path, .db/.xdb file path)
		'''
		try:
			return (PathType.Path if path.endswith(self.paths.SEP) else PathType.File, path, self.paths.gamedata_db_files[path])
		except KeyError: pass

		if not file_wanted:
			# search for path
			if not path.endswith(self.paths.SEP):
				path += self.paths.SEP

			for ff in self.paths.gamedata_db_files.keys():
				if path in ff:
					return (PathType.Path, path, self.paths.gamedata_db_files[path])
		return None

	def exists(self, path: str, file_wanted: bool = True) -> PathType:
		path = self.normalize_path(path)
		if (item := self._find(path, file_wanted)):
			return item[0]
		return PathType.NotExists

	def open(self, path: str, mode: str) -> object | None:
		path = self.normalize_path(path)
		if '+' in mode or 'w' in mode:
			raise self.DbFilesIsReadOnlyFs(f'open(path={path}, {mode=})')
		if (item := self._find(path)):
			_type, path, db_name = item
			# print(f'{item}')
			return DbFileIo(path, str(self.paths.path / db_name), self.paths.config.version)
		return None


class OsGamedataFs(LayerBase):
	'OS filesystem; used for read from gamedata path'


	class OsFilesIsReadOnlyFs(Exception): pass


	def __init__(self, paths: Paths):
		super().__init__()
		self.paths: Paths = paths

	def _find(self, path: str, file_wanted: bool = True) -> tuple[PathType, Path] | None:
		'''finds file in OS gamedata path
		returns (type, OS path)
		'''
		if (f := self.paths.gamedata / self.paths.convert_path_to_os(path)) and f.exists():
			return (PathType.File if f.is_file() else PathType.Path, f)
		return None

	def exists(self, path: str, file_wanted: bool = True) -> PathType:
		if (item := self._find(path, file_wanted)):
			return item[0]
		return PathType.NotExists

	def open(self, path: str, mode: str) -> object | None:
		if '+' in mode or 'w' in mode:
			raise self.OsFilesIsReadOnlyFs(f'open(path={path}, {mode=})')
		if (item := self._find(path)):
			_type, f = item
			# print(f'{item}')
			return f.open(mode if 'b' in mode else 'b' + mode)
		return None


if __name__ == "__main__":
	import argparse
	from sys import argv, stdout, exit
	from os import linesep as LINESEP
	from os.path import basename
	from fnmatch import fnmatch
	from typing import Iterator

	LINESEP_B = LINESEP.encode()
	DEFAULT_GAMEDATA_PATH = 'gamedata'

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description=f'''Odyssey/Stalker Xray game file paths tool; version: {PUBLIC_VERSION} {PUBLIC_DATETIME}

Used to extract files from .db/.xdb files to gamedata or whatever place: see extract sub-command -d option.
Be free to filter extracted files: see extract sub-command -f option examples below; get help: {basename(argv[0])} e -h
And filter .db/.xdb files: see --exclude-db-files option.
Note: while extraction gamedata files is sorted by paths and grouped by .db/.dbx file name.
''',
				epilog=f'''Examples:

1. Extract gamedata files from .db/.xdb files

	Extract all gamedata files from all .db/.xdb files to gamedata sub-folder:
{basename(argv[0])} -g "S.T.A.L.K.E.R" -t 2947ru e

	The same to whatever place:
{basename(argv[0])} -g "S.T.A.L.K.E.R" -t 2947ru e -e "path to extract"

	Extract filtered (from ai\\alife\\ folder) gamedata files from all .db/.xdb files:
{basename(argv[0])} -f "ai\\alife\\*" -g "S.T.A.L.K.E.R" -t 2947ru e

	The same with all .ltx files:
{basename(argv[0])} -f "*.ltx" -g "S.T.A.L.K.E.R" -t 2947ru e

	Extract all gamedata files from filtered .db/.xdb files:
{basename(argv[0])} --exclude-db-files "gamedata.db0" "gamedata.db1" -g "S.T.A.L.K.E.R" -t 2947ru e
{basename(argv[0])} --exclude-db-files "gamedata.db[012]" "gamedata.dbd" -g "S.T.A.L.K.E.R" -t 2947ru e

	Be free to debug command-line use -vv and --dummy:
{basename(argv[0])} -vv -f "ai\\alife\\*" -g "S.T.A.L.K.E.R" -t 2947ru e --dummy

	Create mirror of all gamedata files (.db/.xdb and gamedata sub-path) to another location for debug purposes:
{basename(argv[0])} -g "S.T.A.L.K.E.R" -t 2947ru e --include-gamedata -e "path to extract"
This is a way to find out what an X-ray engine see all game data files.

2. Show info about gamedata files from .db/.xdb files

	Show files info as machine-readable format:
{basename(argv[0])} -g "S.T.A.L.K.E.R" -t 2947ru i

	Show files info as human-readable format (and *.ltx files filter):
{basename(argv[0])} -f "*.ltx" -g "S.T.A.L.K.E.R" -t 2947ru i --table
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', default='.',
				help='game path that contains .db/.xdb files and optional gamedata folder')
			parser.add_argument('--exclude-db-files', metavar='FILE_NAME|PATTERN', nargs='+',
				help='game path that contains .db/.xdb files and optional gamedata folder; Unix shell-style wildcards: *, ?, [seq], [!seq]')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-f', '--filter', metavar='FILE|PATTERN', nargs='+',
				help='filter gamedata files by name use Unix shell-style wildcards: *, ?, [seq], [!seq]')
			parser.add_argument('-d', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata path; used to diff sub-command; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; examples: -v, -vv')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('extract', aliases=('e',), help='extract files from .db/.xdb files')
			parser_.add_argument('-e', '--extract-path', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'destination path to extract files; default: {DEFAULT_GAMEDATA_PATH}')
			parser_.add_argument('-r', '--replace', action='store_true', help='replace existing files')
			parser_.add_argument('--include-gamedata', action='store_true', help='''include files from gamedata sub-path to extract;
used to copy of all gamedata files (.db/.xdb and gamedata sub-path) to another location for debug purposes; default: false
''')
			parser_.add_argument('--encoding', default=DEFAULT_OS_ENCODING, help=f'extract text files encoding to convert to; text files: {", ".join(TEXT_FILES_EXT)}; to binary copy of text files use "raw" encoding; default: {DEFAULT_OS_ENCODING}')
			parser_.add_argument('-m', '--dummy', action='store_true', help='dummy run: do not write files; used for command-line options debugging')
			parser_ = subparsers.add_parser('diff', aliases=('d',), help='compare text files from two medias: .db/.xdb files and gamedata files; output format is unified_diff: ---, +++, @@')
			parser_.add_argument('--encoding', default=DEFAULT_OS_ENCODING, help=f'.db/.xdb text files encoding to convert to; text files: {", ".join(TEXT_FILES_EXT)}; to binary copy of text files use "raw" encoding; default: {DEFAULT_OS_ENCODING}')
			parser_ = subparsers.add_parser('info', aliases=('i',), help='show info about files from .db/.xdb files')
			parser_.add_argument('--paths', action='store_true', help='show paths')
			parser_.add_argument('--table', action='store_true', help='human-readable format')
			parser_.add_argument('--reverse', action='store_true', help='output gamedata file path first')
			return parser.parse_args()

		def get_paths(include_gamedata=False) -> Paths:
			# create main class that manages game paths
			if verbose > 1:
				print('Load all .db/.xdb files to define latest version of gamedata files')
			ret = Paths(Config(args.gamepath, args.version, args.gamedata, args.exclude_db_files, verbose,
				not args.include_gamedata if include_gamedata else True))
			return ret

		def is_gamedata_file_included(path: str) -> bool:
			# check for gamedata files filter as Unix shell pattern
			if args.filter:
				if '.ltx' in path:
					pass
				for include_file in args.filter:
					if '*' in include_file or '?' in include_file or '[' in include_file:
						# filter is pattern
						if fnmatch(path, include_file):
							return True  # export file
					elif include_file == path:  # filter is not pattern
						return True  # export file
				return False  # skip file
			return True

		def iter_db_gamedata_files(p: Paths, skip_paths = True) -> Iterator[tuple[str, list[str]]]:
			'''iters .db/.xdb and their gamedata files
			yields {.db*.xdb file name, [gamedata file path]}
			applies gamedata files filter
			'''
			for f, ff in p.db_gamedata_files.items():
				for fff in ff:
					if skip_paths and fff.endswith(p.SEP):  # skip path
						continue
					if not is_gamedata_file_included(fff):  # filter extracted file by name
						continue  # skip file
					yield (fff, f)

		def iter_gamedata_files(p: Paths, skip_paths = True) -> Iterator[tuple[str, str]]:
			'''iters gamedata file path and corresponding .db/.xdb file name
			yields (gamedata file path, .db*.xdb file name])
			applies gamedata files filter
			'''
			for ff, f in p.gamedata_db_files.items():
				if skip_paths and ff.endswith(p.SEP):  # skip path
					continue
				if not is_gamedata_file_included(ff):  # filter extracted file by name
					continue  # skip file
				yield (ff, f)

		def text_to_os(path: str, buff: bytes) -> str:
			'converts text files to os: encoding and line separator'
			if buff and buff[-1] < 0x20:  # little hack for text files: remove file separator and another control symbols
				buff = buff[:-1]
			if DEFAULT_GAME_LENESEP_B != LINESEP_B:  # is need to convert lines separator
				buff = buff.replace(DEFAULT_GAME_LENESEP_B, LINESEP_B)
			if is_xml_utf_8_file(path, buff):  # is .xml utf-8 ready
				return buff.decode('utf-8')
			return buff.decode(DEFAULT_GAME_ENCODING)

		args = parse_args()
		verbose = args.v

		match args.mode:

			case 'extract' | 'e':
				# extract files from .db/.xdb and optional from gamedata

				def save_file(path: Path, buff: bytes):
					'saves buff to OS file with encoding and linesep conversion for text files'
					if args.encoding != 'raw' and is_text_file(str(path), buff):
						# save text file: convert to encoding
						with path.open('wt', encoding=args.encoding) as f:  # open extracted file on OS filesystem
							f.write(text_to_os(str(path), buff))
					else:
						# save binary file
						with path.open('wb') as f:  # open extracted file on OS filesystem
							f.write(buff)

				# create main class that manages game paths
				p = get_paths(True)

				# define destination path
				extract_path = Path(args.extract_path)
				if not extract_path.is_absolute():
					extract_path = (p.path / extract_path).resolve()  # game path relative
				if verbose:
					print(f'extract path: {extract_path.absolute().resolve()}')

				# check extracted files list
				if not p.gamedata_db_files:
					print('No files to extract')
					return

				# extract file by file grouped by .db/.xdb files to use cached .db/.xdb reader
				stat_write = stat_skip = 0  # files statistics
				prev_f = None
				db_reader: XRReader = None  # cache
				for i, (ff, f) in enumerate(iter_db_gamedata_files(p)):
					pp = (extract_path / p.convert_path_to_os(ff))  # extracted file path
					if not args.replace and pp.exists():  # check is extracted file exists
						if verbose > 1:
							print(f'{i+1:5} {f} skip exist {ff}')
						stat_skip += 1
						continue
					# extract file
					if verbose:
						print(f'{i+1:5} {f} extract {ff}')
					if args.dummy:
						continue  # is dummy run
					# open .db/.xdb file
					if not db_reader or prev_f != f:
						prev_f = f
						db_reader = XRReader(str(p.path / f), p.config.version)
					# find file info in .db/.xdb header chunk and get it data from .db/.xdb file
					for f_f in db_reader.iter_files():
						if f_f.name == ff:
							# file info found
							buff = f_f.get_data(db_reader, not is_text_file(f_f.name))  # enable memoryview for binary files
							break
					# save extracted file data on OS filesystem
					try:  # check is parent path exists
						save_file(pp, buff)
						stat_write += 1
						continue
					except FileNotFoundError: pass  # parent path is not exists
					pp.parent.mkdir(parents=True)  # create parent path
					save_file(pp, buff)
					stat_write += 1
				# all files extracted
				print(f'Total files: check {i+1}, write {stat_write}, skip {stat_skip}, text encoding {args.encoding}, line separator: {str(LINESEP_B if args.encoding != 'raw' else DEFAULT_GAME_LENESEP_B)[1:]} (hex: {(LINESEP_B if args.encoding != 'raw' else DEFAULT_GAME_LENESEP_B).hex()})')

			case 'diff' | 'd':
				# compare files: .db/.xdb and gamedata
				import difflib

				def normalize_lines(lines: Iterable[str]) -> list[str]:
					ret = []
					if '\r\n' != LINESEP:
						for line in lines:
							ret.append(line.rstrip('\n'))
					return ret

				# create main class that manages game paths
				p = get_paths()

				# check extracted files list
				if not p.gamedata_db_files:
					print('No files to compare')
					return
				if verbose > 1:
					print(f'Compare to {p.gamedata.absolute()}')

				# text compare file by file ordered by gamedata file path
				stat_modified = stat_os_missing = stat_os_encoding = 0  # files statistics
				prev_f = None
				db_reader: XRReader = None  # cache
				for i, (ff, f) in enumerate(iter_db_gamedata_files(p)):
					# read text files from two media sources
					if not is_text_file(ff):
						continue  # is not text file
					# get first: .db/.xdb file data
					if verbose > 1:
						print(f'{i+1:5} {ff}')
					# open .db/.xdb file
					if not db_reader or prev_f != f:
						prev_f = f
						db_reader = XRReader(str(p.path / f), p.config.version)
					# find file info in .db/.xdb header chunk and get it data from .db/.xdb file
					for f_f in db_reader.iter_files():
						if f_f.name == ff:
							# file info found
							buff_db = f_f.get_data(db_reader, not is_text_file(f_f.name))  # enable memoryview for binary files
							break
					# with p.open(ff, 'rb') as f1:  # open compared file from OS or .db/.xdb file
					# 	buff_db = f1.read()
					if args.encoding == 'raw':
						try:
							buff_db = buff_db.decode(DEFAULT_GAME_ENCODING).splitlines()
						except UnicodeDecodeError:  # try utf-8 for .xml
							buff_db = buff_db.decode().splitlines()
					else:
						buff_db = text_to_os(ff, buff_db).splitlines()
					# get second: OS file data
					pp = p.gamedata / p.convert_path_to_os(ff)
					try:
						if args.encoding == 'raw':
							with pp.open('rb') as f2:
								buff_os = f2.read()
								try:
									buff_os = buff_os.decode(DEFAULT_GAME_ENCODING).splitlines()
								except UnicodeDecodeError:  # try utf-8 for .xml
									buff_os = buff_os.decode().splitlines()
						else:
							with pp.open('rt', encoding='utf-8') as f2:  # open extracted file on OS filesystem
								try:
									buff_os = normalize_lines(f2.readlines())
								except UnicodeDecodeError as e:
									stat_os_encoding += 1
									print(f'Skip file "{ff}" due to fail text decoding: {e}')
					except FileNotFoundError:
						buff_os = b''
						stat_os_missing += 1
					# compare two files
					is_file_mod = False
					for line in difflib.unified_diff(buff_db, buff_os, f'{f}:{ff}', f'{"OS:".rjust(len(f)+1)+ff}'):
						is_file_mod = True
						stdout.writelines(line)
						if not line.endswith('\n'):
							stdout.writelines('\n')
					if is_file_mod:
						stat_modified += 1
					# stdout.writelines(difflib.unified_diff(buff_db, buff_os, f'{f}:{ff}', f'{"OS:".rjust(len(f)+1)+ff}'))
				# all files compared
				print(f'Total files: compared {i+1}, modified {stat_modified}, os missing {stat_os_missing}{", encoding fail "+str(stat_os_encoding) if stat_os_encoding else ""}')

			case 'info' | 'i':
				# show .db/.xdb gamedata files info

				# create main class that manages game paths
				p = get_paths()

				if p.gamedata_db_files:  # show latest files location: .db/.xdb file and gamedata path/file
					for i, (ff, f) in enumerate(iter_gamedata_files(p, not args.paths)):
						if args.reverse:
							f, ff = ff, f
						if args.table:
							print(f'{i+1:5} {f} {ff}')
						else:
							print(f'{f} {ff}')

		return
	
	try:
		main()
	except WrongDbFormat:
		print('Wrong db file format')
	except UnspecifiedDbFormat:
		print('Unspecified db file format')
	# except UnicodeDecodeError as e:
	# 	print('Wrong file format: ', e)
	except (KeyboardInterrupt, BrokenPipeError):
		exit(0)
