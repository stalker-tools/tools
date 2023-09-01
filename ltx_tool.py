#!/usr/bin/env python3

from collections.abc import Iterator
from sys import stderr
from glob import glob
from os.path import join, dirname, isdir
import locale
from enum import Enum, auto
from re import compile, IGNORECASE, Pattern


class LtxKind(Enum):
	INCLUDE = auto()
	NEW_SECTION = auto()
	LET = auto()
	DATA = auto()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class LtxFileNotFoundException(IOError):
	pass

class Ltx:


	class Section:
		
		def __init__(self, ltx: 'Ltx', name: str, section: dict) -> None:
			self.name, self.ltx, self.section = name, ltx, section

		def get(self, value_name: str, default_value: object | None = None) -> object | None:
			'gets value of section or parent sections'
			return self._get_value(self.ltx.sections, self.section, value_name, default_value)
		
		@classmethod
		def _get_value(cls, sections, section, value_name: str, default_value: object | None = None) -> object | None:
			if value_name in section:
				return section.get(value_name, default_value)
			# try find value in parent sections
			if (parents := section.get('')):
				for parent in parents:
					if (parent_section := sections.get(parent)):
						if (value := cls._get_value(sections, parent_section, value_name, default_value)) is not None:
							return value
			return None


	def __init__(self, ltx_file_path: str, follow_includes=True) -> None:
		self.ltx_file_path = ltx_file_path
		self.sections: dict = self._get_ltx_dict(ltx_file_path, follow_includes)

	def _get_ltx_dict(self, ltx_file_path: str, follow_includes=True) -> dict[str, dict[str, object]] | None:
		sections, section = {}, {}
		prev_section_name = None
		for x in parse_ltx_file(ltx_file_path, follow_includes=follow_includes):
			match x:
				case (LtxKind.NEW_SECTION, section_name, section_parents):
					if section_name in sections:
						print(f'duplicated section name: {section_name}', file=stderr)
					if len(section) > 1:
						sections[prev_section_name] = section
					section = { '': section_parents }  # set parent sections names
					prev_section_name = section_name
				case (LtxKind.LET, _, _, lval, rvals):
					section[lval] = rvals if len(rvals) > 1 else rvals[0]
		if len(section) > 1:
			sections[prev_section_name] = section
		if sections:
			return sections
		return None

	def iter_sections(self) -> Iterator[Section]:
		if self.sections:
			for section_name, section_dict in self.sections.items():
				yield self.Section(self, section_name, section_dict)


SECTION_RE = compile('^\[([\S]+)\]:?(.*)$')

def get_filters_re_compiled(search_patterns: list[str] | None) -> tuple[Pattern] | None:

	def re_escape(search_pattern: str) -> str:
		ret = search_pattern.replace('*', '.*')
		ret = ret.replace('^', '\^').replace('$', '\$')
		ret = ret.replace('(', '\(').replace(')', '\)')
		ret = ret.replace('[', '\[').replace(']', '\]')
		ret = ret.replace('?', '\?').replace('!', '\!')
		return ret

	return tuple(compile('^' + re_escape(x) + '$', IGNORECASE) for x in search_patterns) if search_patterns else None

def is_filters_re_match(re_filters: tuple[Pattern] | None, value: str | None) -> bool:
	if not re_filters:
		return True
	if not value:
		return False
	return any(map(lambda r: r.match(value), re_filters))

def remove_comment(line: bytearray) -> str:
	return line.partition(b';')[0].strip()

def try_decode(buff: bytearray, encoding=locale.getpreferredencoding()) -> str:
	try:
		return buff.decode(encoding)
	except:
		# try to read as UTF-8 (it can happend)
		try:
			return buff.decode('utf-8')
		except:
			# hard case - just escape the symbols
			return buff.decode(encoding, 'backslashreplace')

def parse_ltx_file(file_path: str, follow_includes=False):
	section_name = None
	try:
		with open(file_path, 'rb') as f:
			for line_index, line in enumerate(f.readlines()):
				# print(f'{line=}')
				line = line.strip(b' \t\r\n')
				if not line or line.startswith(b';'):
					pass  # ignore empty or comment line
				elif line.startswith(b'#include'):
					# include another ltx file
					line = remove_comment(line)
					include_file_path = line[len(b'#include'):].strip(b' \t"')
					include_file_path = include_file_path.replace(b'\\', b'/')
					include_file_path = try_decode(include_file_path)
					yield LtxKind.INCLUDE, line_index, include_file_path
					if follow_includes:
						# pass multiplayer files
						if file_path.startswith('mp/'):
							continue
						yield from parse_ltx_file(join(dirname(file_path), include_file_path), True)
				else:
					# process line
					line = remove_comment(line)
					line = try_decode(line)
					if line.startswith('['):
						# new section starts
						section_name, section_parents = SECTION_RE.findall(line)[0]
						if section_name:
							yield LtxKind.NEW_SECTION, section_name, section_parents.split(',') if section_parents else None
					elif '=' in line:
						# let expression
						lval, _, rval = line.partition('=')
						yield LtxKind.LET, line_index, section_name, lval.strip(), tuple(map(lambda x: x.strip(), rval.split(',')))
					else:
						yield LtxKind.DATA, section_name, map(lambda x: x.strip(), line.split(','))

	except IOError as e:
		if not follow_includes:
			raise LtxFileNotFoundException(e)


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray .ltx file parser',
				epilog=f'Examples: {argv[0]} -f 1.ltx 2.ltx',
			)
			parser.add_argument('-f', '--ltx', metavar='FILE_PATH', required=True, nargs='+', help='one or more paths of directories and/or .ltx files')
			parser.add_argument('-p', metavar='SECTION NAMES', nargs='*', help='show all descendants of this parents; regexp, escaped symbols: ^$()[]?!')
			parser.add_argument('-s', metavar='SECTION NAMES', nargs='*', help='section name filter; regexp, escaped symbols: ^$()[]?!')
			parser.add_argument('-l', metavar='LET RLVALUES', nargs='*', help='left value filter for assign; regexp, escaped symbols: ^$()[]?!')
			parser.add_argument('-r', action='store_true', help='show info reversed')
			parser.add_argument('-m', metavar='VALUE', help='modify (set) value')
			return parser.parse_args()

		args = parse_args()

		is_lvalue_filter = bool(args.l)

		def is_re_match(re_patterns, value: str | list[str]) -> bool:
			if type(value) is str:
				for re_pattern in re_patterns:
					if re_pattern.match(value):
						return True
			else:
				for v in value:
					for re_pattern in re_patterns:
						if re_pattern.match(v):
							return True
			return False

		parent_section_name_patterns = get_filters_re_compiled(args.p)
		section_name_patterns = get_filters_re_compiled(args.s)
		lvalue_patterns = get_filters_re_compiled(args.l)
		is_edit = bool(args.m)

		def line_find(line: str | bytes, what: list[bytes | str], start_index=0):
			ret = len(line)
			for w in what:
				if (i := line.find(w, start_index)) >= 0 and i < ret:
					ret = i
			return ret

		def print_ltx_file(file_path: str):

			def is_section_name_filtered(name: str | None) -> bool:
				if parent_section_name_patterns:  # filter by parens sections
					if section_parents:
						if is_re_match(parent_section_name_patterns, section_parents):
							return False  # show parent section
					return True
				if section_name_patterns:  # filter by section name
					if not name:
						return True
					if is_re_match(section_name_patterns, name):
						return False
				else:
					return False  # filter not defined
				return True

			def is_lvalue_filtered(lvalue: str) -> bool:
				if lvalue_patterns:
					if is_re_match(lvalue_patterns, lvalue):
						return False
				else:
					return False  # filter not defined
				return True

			print_path = file_path[file_path.index('gamedata') + len('gamedata') + 1:] if 'gamedata' in file_path else file_path
			section_parents = None
			lines_indexes: dict[int, str] = {}
			for x in parse_ltx_file(file_path):
				match x[0]:
					case LtxKind.NEW_SECTION:
						section_parents = x[2]
						if is_lvalue_filter or is_section_name_filtered(x[1]):
							continue
						if x[2]:
							# section with parents
							if args.r:
								print(f'[{x[1]}]:{",".join(x[2])} {bcolors.HEADER}{print_path}{bcolors.ENDC}')
							else:
								print(f'{bcolors.HEADER}{print_path}{bcolors.ENDC} [{x[1]}]:{",".join(x[2])}')
						else:
							# section without parents
							if args.r:
								print(f'[{x[1]}] {bcolors.HEADER}{print_path}{bcolors.ENDC}')
							else:
								print(f'{bcolors.HEADER}{print_path}{bcolors.ENDC} [{x[1]}]')
					case LtxKind.LET:
						if is_lvalue_filtered(x[3]) or is_section_name_filtered(x[2]):
							continue
						if args.r:
							print(f'{x[3]} = {", ".join(x[4])} {bcolors.OKBLUE}[{x[2]}]{bcolors.ENDC} {bcolors.HEADER}{print_path}{bcolors.ENDC}')
						else:
							print(f'{bcolors.HEADER}{print_path}{bcolors.ENDC} {bcolors.OKBLUE}[{x[2]}]{bcolors.ENDC} {x[3]} = {", ".join(x[4])}')
						if is_edit:
							lines_indexes[x[1]] = x[2]
					case LtxKind.DATA:
						if is_lvalue_filter or is_section_name_filtered(x[1]):
							continue
						print(f'{bcolors.HEADER}{print_path}{bcolors.ENDC} {bcolors.OKBLUE}[{x[1]}]{bcolors.ENDC} {",".join(x[2])}')
			return lines_indexes

		def edit_ask() -> bool:
			while True:
				anwer = input('edit file (y, N, e[xit]) ? : ')
				match anwer.strip():
					case 'y' | 'Y':
						return True
					case '' | 'n' | 'N':
						return False
					case f as str if f.lower() in 'exit':
						from sys import exit; exit(0)

		for path_ in args.ltx:
			if isdir(path_):
				for path_ in glob(join(path_, '**/*.ltx'), recursive=True):
					lines_indexes = print_ltx_file(path_)
					if lines_indexes:
						# edit file
						# print(f'{lines_indexes=}')
						if not edit_ask():
							break
						with open(path_, 'rb') as f:
							lines = f.readlines()
						with open(path_, 'wb') as f:
							for line_index, line in enumerate(lines):
								if (section_name := lines_indexes.get(line_index)):
									eq_index = line.find(b'=')
									end_index = line_find(line, (b';', b'\r', b'\n'), eq_index)
									line = bytearray(line)
									line[eq_index + 1:end_index] = args.m.encode()
									print(f'{bcolors.HEADER}{line_index + 1:03}{bcolors.ENDC} {bcolors.OKBLUE}[{section_name}]{bcolors.ENDC} {line.decode().strip()}')
								f.write(line)
			else:
				for path_2 in glob(path_, recursive=True):
					print_ltx_file(path_2)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
