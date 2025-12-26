
# Xray .db/.xdb files reader
# Author: Stalker tools, 2023-2025

from typing import Iterator
from enum import IntEnum
from pathlib import Path
import lzo
# tools imports
from SequensorReader import SequensorReader
from LzHuf import LzHuf
from Scrambler import XRScrambler, XRScramblerConfig


class DbVersion(IntEnum):
	DB_VERSION_AUTO		= 0
	DB_VERSION_1114		= 0x01
	DB_VERSION_2215		= 0x02
	DB_VERSION_2945		= 0x04
	DB_VERSION_2947RU	= 0x08
	DB_VERSION_2947WW	= 0x10
	DB_VERSION_XDB		= 0x20


class ChunkTypes(IntEnum):
	DB_CHUNK_DATA		= 0
	DB_CHUNK_HEADER		= 1
	DB_CHUNK_USERDATA	= 0x29a
	CHUNK_COMPRESSED	= 0x80000000
	DB_CHUNK_MASK		= CHUNK_COMPRESSED ^ ((1 << CHUNK_COMPRESSED.bit_length()) - 1)  # ~CHUNK_COMPRESSED


class WrongDbFormat(Exception): pass


class UnspecifiedDbFormat(Exception): pass


class DbFileOverrun(Exception): pass


class XRReader:

	# binary access classes

	class Chunk:
		'base chunk to read .db/.xdb file'

		def __init__(self, type: int, size: int, parent_sr: SequensorReader) -> None:
			try:
				self.type, self.size, self.parent_pos = ChunkTypes(type & ChunkTypes.DB_CHUNK_MASK), size, parent_sr.pos
				self.buff = parent_sr.buff
				self.is_compressed = bool(type & ChunkTypes.CHUNK_COMPRESSED)
			except ValueError:
				raise WrongDbFormat()
			self._check()

		def __str__(self) -> str:
			return f'Chunk type={self.type.name}({self.type}) offset={self.parent_pos:_} size={self.size:_} {"compressed" if self.is_compressed else ""}'

		def _check(self) -> None:
			if self.parent_pos + self.size > len(self.buff):
				raise DbFileOverrun()

		def get_data(self) -> bytes:
			'returns chunk binary data'
			self._check()
			return self.buff[self.parent_pos:self.parent_pos + self.size]

	# files/path access classes

	class FileOrPath:

		def __init__(self, sr: SequensorReader) -> None:
			self.sr = sr
			# must be defined by inheritance classes:
			self.crc = None
			self.name = None
			self.size_real = self.offset = self.size_compressed = None

		def __str__(self) -> str:
			return self.name if self.name else ''

		@classmethod
		def get_table_header(cls):
			return f'Type Offset  Compressed    CRC       Size    Name'

		def get_table_row(self):
			return f'{"F" if self.is_file else "D"} 0x{self.offset:08x} {self.size_compressed: 9_} 0x{self.crc:08x} {self.size_real: 9_} {self.name}'

		@property
		def is_file(self) -> bool:
			'returns True: is file; False: is path'
			return bool(self.offset)

		@property
		def size(self) -> int:
			return self.size_real

		def skip_data(self) -> None:
			'skips file data'
			self.sr.skip(self.size_compressed)

		def get_data(self, db_reader: 'XRReader', keep_mv = False) -> bytes | None:
			'gets file data or None for path from data chunk'
			if self.is_file:
				raw_data = db_reader.sr.buff[self.offset:self.offset+self.size_compressed]
				if self.size_compressed == self.size_real:  # is not need to decompress
					if not keep_mv:  # not keep memoryview
						raw_data = bytes(raw_data)
					return raw_data
				return lzo.decompress(raw_data, False, self.size_real, algorithm='LZO1X')
			else:
				return None


	class FileOrPath_1114(FileOrPath):

		def __init__(self, sr: SequensorReader) -> None:
			XRReader.FileOrPath.__init__(self, sr)
			self.name = sr.read_string()
			self.size_real, self.offset, self.size_compressed = sr.read('III')

		def get_data(self) -> bytes | None:
			'gets file data or None for path'
			if self.is_file:
				raw_data = self.sr.read_bytes(self.size_compressed)
				if self.size_real:
					return raw_data
				if (buff := LzHuf.Decode(raw_data, len(raw_data))):
					return buff
			return None


	class FileOrPath_2215(FileOrPath):

		def __init__(self, sr: SequensorReader) -> None:
			XRReader.FileOrPath.__init__(self, sr)
			self.name = sr.read_string()
			self.offset, self.size_real, self.size_compressed = sr.read('III')


	class FileOrPath_2945(FileOrPath):

		def __init__(self, sr: SequensorReader) -> None:
			XRReader.FileOrPath.__init__(self, sr)
			self.name = sr.read_string()
			self.crc, self.offset, self.size_real, self.size_compressed = sr.read('IIII')


	class FileOrPath_2947(FileOrPath):

		def __init__(self, sr: SequensorReader) -> None:
			XRReader.FileOrPath.__init__(self, sr)
			name_size, self.size_real, self.size_compressed, self.crc = sr.read('HIII')
			self.name, self.offset = sr.read_bytes(name_size - 16).decode(), sr.read('I')


	def __init__(self, file_path: str | Path, version: str) -> None:
		self.file_path = Path(file_path)
		self._buff: bytes | None = None
		self.sr = self._read_file()  # read .db file and create chunk reader
		self.version = DbFileVersion.get_version_by_file_name(self.file_path, version)
		self._header_chunk_sr: SequensorReader | None = None  # SR cache

	def _read_file(self) -> SequensorReader:
		'read .db file'
		with open(self.file_path, 'rb') as f:
			# init chunk reader
			self._buff = f.read()
			sr = SequensorReader(memoryview(self._buff))
			return sr

	def iter_chunks(self) -> Iterator[Chunk]:
		'iters chunks from beginning of file'
		if self.sr:
			self.sr.pos = 0
			while self.sr.pos < len(self.sr.buff):
				type, size = self.sr.read('II')
				yield self.Chunk(type, size, self.sr)
				self.sr.skip(size)

	def find_chunk(self, _type: ChunkTypes) -> Chunk | None:
		'finds chunk from beginning of file'
		for chunk in self.iter_chunks():
			if chunk.type == _type:
				return chunk
		return None

	def _unscramble_chunk(self, chunk: Chunk) -> bytes:
		# returns unscrambled chunk according to .db file version

		def unscramble(buff: bytes, config: XRScramblerConfig) -> bytes:
			scrambler = XRScrambler(config)
			buff = scrambler.decrypt(buff)
			lz_huf = LzHuf()
			buff = lz_huf.Decode(buff)
			return buff

		# get chunk raw data
		buff = chunk.get_data()
		# decrypt and/or decompress chunk data
		match self.version:
			case DbVersion.DB_VERSION_1114 |\
					DbVersion.DB_VERSION_2215 |\
					DbVersion.DB_VERSION_2945 |\
					DbVersion.DB_VERSION_XDB:
				if chunk.is_compressed:
					buff = LzHuf.Decode(buff, len(buff))
			case DbVersion.DB_VERSION_2947RU:
				if chunk.is_compressed:
					buff = unscramble(buff, XRScramblerConfig.CC_RU)
			case DbVersion.DB_VERSION_2947WW:
				if chunk.is_compressed:
					buff = unscramble(buff, XRScramblerConfig.CC_WW)
		return buff

	DB_VERSION_FILE_OR_PATH = {
		DbVersion.DB_VERSION_1114: FileOrPath_1114,
		DbVersion.DB_VERSION_2215: FileOrPath_2215,
		DbVersion.DB_VERSION_2945: FileOrPath_2945,
		DbVersion.DB_VERSION_2947RU: FileOrPath_2947,
		DbVersion.DB_VERSION_2947WW: FileOrPath_2947,
		DbVersion.DB_VERSION_XDB: FileOrPath_2947,
	}

	def _get_file_or_path_type(self) -> FileOrPath:
		# returns type of files iterator according to .db file version
		return self.DB_VERSION_FILE_OR_PATH[self.version]

	def iter_files(self) -> Iterator[FileOrPath]:
		# iters files or paths

		f_type = self._get_file_or_path_type()

		if self._header_chunk_sr:  # is cache created
			self._header_chunk_sr.pos = 0  # reset pointer to iter from beginning
			while self._header_chunk_sr.remain:  # iter paths and files
				yield f_type(self._header_chunk_sr)
		elif (chunk := self.find_chunk(ChunkTypes.DB_CHUNK_HEADER)):
			if chunk.size:
				# head chunk found # decrypt and/or decompress chunk data
				buff = self._unscramble_chunk(chunk)
				# iter paths and files from decompressed head chunk data: buff
				self._header_chunk_sr = sr = SequensorReader(buff)  # create SR and set SR cache
				while sr.remain:  # iter paths and files
					yield f_type(sr)
			else:
				print('Found head chunk but it has zero size')

	def process(self):
		for f in self.iter_files():
			print(str(f))
			if (buff := f.get_data()):
				# is file
				pass
			else:
				# is path
				print(f'\tcreate path')
				# f.skip_data()


class DbFileVersion:

	FILE_VERSIONS = {
		'11xx': DbVersion.DB_VERSION_1114,
		'2215': DbVersion.DB_VERSION_2215,
		'2945': DbVersion.DB_VERSION_2945,
		'2947ru': DbVersion.DB_VERSION_2947RU,
		'2947ww': DbVersion.DB_VERSION_2947WW,
		'xdb': DbVersion.DB_VERSION_XDB,
		}

	@classmethod
	def get_versions_names(cls) -> tuple[str]:
		return cls.FILE_VERSIONS.keys()

	@classmethod
	def get_version_by_name(cls, version_name: str) -> DbVersion:
		return cls.FILE_VERSIONS[version_name] if version_name else DbVersion.DB_VERSION_AUTO

	@classmethod
	def get_version_by_file_name(cls, file_name: Path, version_name: str) -> DbVersion:
		if (version := cls.get_version_by_name(version_name)) == DbVersion.DB_VERSION_AUTO:
			# try to define file version by extention
			file_ext = file_name.suffix
			if len(file_ext) == 5 and file_ext.startswith('.xdb') and file_ext[4].isalnum():
				version = DbVersion.DB_VERSION_XDB
			elif file_ext == '.xrp':
				version = DbVersion.DB_VERSION_1114
			elif len(file_ext) == 4 and file_ext.startswith('.xp') and file_ext[3].isalnum():
				version = DbVersion.DB_VERSION_2215
		# check defined version
		if (version == DbVersion.DB_VERSION_AUTO or (version.value & (version.value - 1)) != 0):
			raise UnspecifiedDbFormat()
		return version


if __name__ == "__main__":
	import argparse
	from sys import argv, stdout, exit
	from os.path import basename
	from glob import glob
	from fnmatch import fnmatch

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='DBReader test',
				epilog=f'''Examples:

1. Overal gamedata files

1.1 Gamedata overall in all .db files

	Show all files in all .db game files:
{basename(argv[0])} -f "gamedata.db*" -t 2947ru g

	Show .script files (Unix shell pattern) in selected .db game files (GLOB pattern):
{basename(argv[0])} -f "gamedata.db[04]" -t 2947ru g -g "*.script"

	Show latest version files from all .db game files:
{basename(argv[0])} -f "gamedata.db*" -t 2947ru g -l -g "*dialog*.script"

	Count files in all .db game files:
{basename(argv[0])} -f "gamedata.db*" -t 2947ru g -c

1.2 Gamedata separated by .db files

	Count files by .db game files:
{basename(argv[0])} -f "gamedata.db*" -t 2947ru g -s -c

	Count .script files by .db game files:
{basename(argv[0])} -f "gamedata.db*" -t 2947ru g -s -c -g "*.script"

2. One .db file

	Show files info (names only):
{basename(argv[0])} -f gamedata.dbd" -t 2947ru f

	Show files info as table format:
{basename(argv[0])} -f gamedata.dbd" -t 2947ru f --table

3. Examples for development purposes

	Show files info from unscrambled header chunk binary file:
{basename(argv[0])} -f "gamedata.dbd.header-unscrambled.bin" -t 2947ru f --header

	Show chunks info:
{basename(argv[0])} -f "gamedata.dbd" -t 2947ru i

	Dump raw header chunk to binary file:
{basename(argv[0])} -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"

	Dump raw chunk (by index) to binary file:
{basename(argv[0])} -f "gamedata.dbd" -t 2947ru d -i 1 > "gamedata.dbd.chunk-1.bin"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-f', metavar='PATH', required=True,
				help='.db file path; for gamedata sub-command: GLOB pattern; for another sub-commands: path to .db file')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db files version; usually 2947ru/2947ww for SC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-v', action='store_true', help='verbose mode')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('gamedata', aliases=('g',), help='gamedata files and .db files manipulations')
			parser_.add_argument('-g', '--filter', metavar='PATTERN',
				help='filter files by name use Unix shell-style wildcards: *, ?, [seq], [!seq]')
			parser_.add_argument('-s', '--split', action='store_true', help='show files by .db files')
			parser_.add_argument('-n', '--number', action='store_true', help='show number the files')
			parser_.add_argument('-c', '--count', action='store_true', help='count files')
			parser_.add_argument('-l', '--last', action='store_true', help='show .db file of latest version of file')
			parser_ = subparsers.add_parser('files', aliases=('f',), help='one .db file: show files info')
			parser_.add_argument('--table', action='store_true', help='show files as table format')
			parser_.add_argument('--header', action='store_true', help='treat file as header chunk binary dump file')
			parser_ = subparsers.add_parser('info', aliases=('i',), help='one .db file: dump chunks info')
			parser_ = subparsers.add_parser('dump', aliases=('d',), help='one .db file: dump chunks raw data')
			parser_.add_argument('-i', metavar='NUMBER', type=int, help='print chunk by index: 0..')
			parser_.add_argument('--header', action='store_true', help='print header chunk')
			return parser.parse_args()

		args = parse_args()
		verbose = args.v

		if verbose:
			print(f'File: {Path(args.f).name}')

		match args.mode:
			case 'gamedata' | 'g':

				def iter_db_files() -> Iterator[Path]:
					# iters sorted gamedata .db files according to GLOB file name filter
					for f in sorted(Path(x) for x in glob(args.f)):
						if not f.is_file():
							continue
						yield f

				def iter_files_in_db_file(db_reader: XRReader) -> Iterator[XRReader.FileOrPath]:
					# iters files (in .db file) according to file name filter
					for f in (x for x in db_reader.iter_files() if x.is_file):
						if not args.filter:
							yield f
						elif fnmatch(f.name, args.filter):  # Unix shell-style wildcards
							yield f

				if args.split:
					# files by .db files
					db_pref = '' if args.count else '\t'
					for i, f in enumerate(iter_db_files()):
						if args.number:
							print(f'{db_pref}{i + 1:02} {f.name}', end=' ' if args.count else '\n')
						else:
							print(f'{db_pref}{f.name}', end=' ' if args.count else '\n')
						# open .db file
						db_reader = XRReader(f, args.version)
						if args.count:  # count files in .db file
							print(f'{sum(1 for _ in iter_files_in_db_file(db_reader)):5}')
						else:
							for ii, ff in enumerate(iter_files_in_db_file(db_reader)):
								if args.number:
									print(f'{ii + 1} {ff.name}')
								else:
									print(ff.name)
				else:
					# files for all .db files
					if args.last:  # show last version of files
						files = {}  # gamedata file: .db file
						for i, f in enumerate(iter_db_files()):
							# open .db file
							db_reader = XRReader(f, args.version)
							for ff in iter_files_in_db_file(db_reader):
								files[ff.name] = f.name
						if files:
							if args.number:
								max_ff_len = max(len(x) for x in files.keys())
							for i, (ff, f) in enumerate(sorted(files.items(), key=lambda x: x[0])):
								if args.number:
									print(f'{i + 1:5} {ff:{max_ff_len}} {f}')
								else:
									print(f'{ff} {f}')
						elif verbose:
							print('<No files>')
					else:
						files = set()  # files names
						for i, f in enumerate(iter_db_files()):
							# open .db file
							db_reader = XRReader(f, args.version)
							for ff in iter_files_in_db_file(db_reader):
								files.add(ff.name)
						if args.count:  # count files in .db file
							print(f'{len(files)}')
						else:
							for ii, ff in enumerate(sorted(files)):
								if args.number:
									print(f'{ii + 1:>5} {ff}')
								else:
									print(ff)

			case 'files' | 'f':

				def iter_files() -> Iterator[XRReader.FileOrPath]:
					db_reader = XRReader(args.f, args.version)
					if args.header:
						# from header dump binary file
						f_type = db_reader._get_file_or_path_type()
						while db_reader.sr.remain:  # iter paths and files
							yield f_type(db_reader.sr)
					else:
						for f in db_reader.iter_files():  # iter paths and files
							yield f

				if args.table:
					print(XRReader.FileOrPath.get_table_header())
				for f in iter_files():
					if args.table:
						print(f.get_table_row())
					else:
						print(f)

			case 'info' | 'i':
				db_reader = XRReader(args.f, args.version)
				for i, chunk in enumerate(db_reader.iter_chunks()):
					print(i, chunk)

			case 'dump' | 'd':
				if args.header:
					# print header chunk
					db_reader = XRReader(args.f, args.version)
					if (chunk := db_reader.find_chunk(ChunkTypes.DB_CHUNK_HEADER)):
						if chunk.size:
							# head chunk found
							buff = chunk.get_data()
							if verbose:
								print(chunk)
								print(buff)
							else:
								stdout.buffer.write(buff)
				elif (chunk_index := args.i) is not None and chunk_index >= 0:
					# print chunk by index
					db_reader = XRReader(args.f, args.version)
					for i, chunk in enumerate(db_reader.iter_chunks()):
						if i == chunk_index:
							buff = chunk.get_data()
							if verbose:
								print(i, chunk)
								print(buff)
							else:
								stdout.buffer.write(buff)
	
	try:
		main()
	except WrongDbFormat:
		print('Wrong db file format')
	except UnspecifiedDbFormat:
		print('Unspecified db file format')
	except UnicodeDecodeError:
		print('Wrong file format')
	except (KeyboardInterrupt, BrokenPipeError):
		exit(0)
