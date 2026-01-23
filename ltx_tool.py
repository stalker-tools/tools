#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker X-ray game .ltx configuration files tool
# Author: Stalker tools, 2023-2026

from collections.abc import Iterator
from sys import stderr
from glob import glob
from os.path import join, dirname, isdir, sep
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
	'Ltx file'

	class Section:
		'Ltx file section'

		__slots__ = ('name', 'ltx', 'section')
		
		def __init__(self, ltx: 'Ltx', name: str, section: dict) -> None:
			self.name, self.ltx, self.section = name, ltx, section

		def __str__(self) -> str:
			ret = f'[{self.name}] ; {{{self.ltx.ltx_file_path}}}'
			for name in self.iter_names(True):
				ret += f'\n\t{name}={self.get(name)}'
			return ret

		def get(self, value_name: str, default_value: object | None = None) -> object | None:
			'gets value of section or parent sections'
			return self._get_value(self.ltx.sections, self.section, value_name, default_value)
		
		@classmethod
		def _get_value(cls, sections: dict[str, 'Ltx.Section'], section: dict, value_name: str, default_value: object | None = None) -> object | None:
			if value_name in section:
				return section.get(value_name, default_value)
			# try find value in parent sections
			if (parents := section.get('')):  # is any parent
				for parent in parents:  # loop thru parent sections names
					if (parent_section := sections.get(parent)):
						if (value := cls._get_value(sections, parent_section, value_name, default_value)) is not None:
							return value
			return None

		def iter_parent_sections(self) -> Iterator['Ltx.Section']:
			if (parents := self.section.get('')):  # is any parent
				for parent in parents:  # loop thru parent sections names
					if (parent_section := self.ltx.sections.get(parent)):
						yield parent_section

		def iter_names(self, include_parents = False) -> Iterator[str]:
			'iterates section values names'
			for name in self.section:
				if name:
					yield name
			# iter values in parent sections
			if include_parents:
				for section in self.iter_parent_sections():
					for name in section:
						yield name


	def __init__(self, ltx_file_path: str, follow_includes = True, open_fn = open, verbose = 0) -> None:
		self.ltx_file_path = ltx_file_path
		self.line_number = None  # included .ltx line number
		self.open_fn = open_fn  # open function; used to files open: either .db/.xdb or OS filesystem
		self.ltxs: list[Ltx] = []
		self.sections: dict[str, Ltx.Section] = {}
		self.verbose = verbose
		self._load_tree()
		# self.ltxs: list[Ltx] = self._get_ltxs(ltx_file_path, follow_includes)

	def _load_tree(self, follow_includes=True):
		'return list of included Ltx'
		sections, section = {}, {}
		prev_section_name = None
		if self.verbose > 1:
			print(f'{self.ltx_file_path}')
		for x in parse_ltx_file(self.ltx_file_path, False, open_fn=self.open_fn):
			match x:
				case (LtxKind.INCLUDE, line_number, included_ltx_file_path):
					if follow_includes:
						try:
							ltx = Ltx(join(dirname(self.ltx_file_path), included_ltx_file_path), True, open_fn=self.open_fn, verbose=self.verbose)
							ltx.line_number = line_number
							self.ltxs.append(ltx)
						except LtxFileNotFoundException:
							pass
				case (LtxKind.NEW_SECTION, section_name, section_parents):
					if section_name in sections:
						print(f'duplicated section name: {section_name}', file=stderr)
					if len(section) > 1:
						sections[prev_section_name] = section
					section = { '': section_parents }  # set parent sections names
					prev_section_name = section_name
				case (LtxKind.LET, _, _, lval, rvals):
					section[lval] = rvals if len(rvals) > 1 else rvals[0]
				case (LtxKind.DATA, _, lval):
					for _lval in lval:
						section[_lval] = None
		if len(section) > 1:  # if section not empty
			sections[prev_section_name] = section
		if sections:
			self.sections = sections

	def _get_ltxs(self, ltx_file_path: str, follow_includes=True) -> dict[str, dict[str, object]] | None:
		'return list of included Ltx'
		sections, section = {}, {}
		prev_section_name = None
		for x in parse_ltx_file(ltx_file_path, follow_includes=follow_includes, open_fn=self.open_fn):
			match x:
				case (LtxKind.INCLUDE, line_number, included_ltx_file_path):
					ltx = Ltx(included_ltx_file_path, True, open_fn=self.open_fn)
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

	def iter_sections(self, included = True) -> Iterator['Ltx.Section']:
		# iter sections
		if self.sections:
			for section_name, section_dict in self.sections.items():
				yield self.Section(self, section_name, section_dict)
		# iter included .ltx sections
		if included:
			for ltx in self.ltxs:
				yield from ltx.iter_sections()


SECTION_RE = compile(r'^\[([\S]+)\]:?(.*)$')

def get_filters_re_compiled(search_patterns: list[str] | None) -> tuple[Pattern] | None:

	def re_escape(search_pattern: str) -> str:
		ret = search_pattern.replace('*', '.*')
		ret = ret.replace(r'^', r'\^').replace(r'$', r'\$')
		ret = ret.replace(r'(', r'\(').replace(r')', r'\)')
		ret = ret.replace(r'[', r'\[').replace(r']', r'\]')
		ret = ret.replace(r'?', r'\?').replace(r'!', r'\!')
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

MULTIPLAYER_PATH = f'{sep}mp{sep}'

def parse_ltx_file(file_path: str, follow_includes=False, open_fn = open) -> Iterator[
		tuple[LtxKind, int, str] |
		tuple[LtxKind, str, tuple | None] |
		tuple[LtxKind, int, str, str, tuple] |
		tuple[LtxKind, str, tuple]
		]:
	'iter .ltx file: LtxKind.INCLUDE, LtxKind.NEW_SECTION, LtxKind.LET, LtxKind.DATA'
	# exclude multiplayer files
	if MULTIPLAYER_PATH in file_path.lower():
		return
	section_name = None
	try:
		with open_fn(file_path, 'rb') as f:
			for line_index, line in enumerate(f.readlines()):
				# print(f'{line=}')
				line = line.strip(b' \t\r\n')
				if not line or line.startswith(b';'):
					pass  # ignore empty or comment line
				elif line.startswith(b'#include'):
					# include another ltx file
					# example: #include "upgrades\w_ak74_up.ltx"
					line = remove_comment(line)
					include_file_path = line[len(b'#include'):].strip(b' \t"')
					if sep != '\\':
						include_file_path = include_file_path.replace(b'\\', sep.encode())
					include_file_path = try_decode(include_file_path)
					yield LtxKind.INCLUDE, line_index, include_file_path
					if follow_includes:
						yield from parse_ltx_file(join(dirname(file_path), include_file_path), True, open_fn=open_fn)
				else:
					# process line
					line = remove_comment(line)
					line = try_decode(line)
					if line.startswith('['):
						# new section starts
						# example: [ammo_base]:identity_immunities,default_weapon_params
						section_name, section_parents = SECTION_RE.findall(line)[0]
						if section_name:
							yield LtxKind.NEW_SECTION, section_name, section_parents.split(',') if section_parents else None
					elif '=' in line:
						# let expression
						# example: position = -0.021, -0.085, 0.0
						lval, _, rval = line.partition('=')
						yield LtxKind.LET, line_index, section_name, lval.strip(), tuple(map(lambda x: x.strip(), rval.split(',')))
					else:
						# example: 255,255,000,255
						yield LtxKind.DATA, section_name, map(lambda x: x.strip(), line.split(','))

	except IOError as e:
		if not follow_includes:
			raise LtxFileNotFoundException(e)

def get_section_line_index(section: Ltx.Section, value_name: str | list[str], open_fn = open) -> int | dict[str, int] | None:
	'gets line index of .ltx file section and lvalue'

	def is_value_name(lvalue: str) -> bool:
		if value_name_is_str:
			return lvalue == value_name
		return lvalue in value_name

	value_name_is_str = type(value_name) is str
	if not value_name_is_str:
		ret = {}
	is_section_body = False  # used to parse section into .ltx file
	for x in parse_ltx_file(section.ltx.ltx_file_path, open_fn=open_fn):
		match x[0]:
			case LtxKind.NEW_SECTION:
				if is_section_body:
					# section was read but value with name were not found
					if value_name_is_str:
						return None
					return ret  # return found values
			case LtxKind.LET:
				if section.name == x[2]:  # check section name
					is_section_body = True
					if is_value_name(x[3]):  # check value name (lvalue)
						# value found
						if value_name_is_str:
							return x[1]  # line index
						ret[x[3]] = x[1]  # value name (lvalue) = line index
						if len(ret) == len(value_name):
							return ret  # all value names found
	if value_name_is_str:
		return None  # value name not found
	return ret

def update_section_value(section: Ltx.Section, value_name: str, new_value: str, open_fn = open) -> bool:
	'updates lvalue of .ltx file section'

	def find_in_line(line: str | bytes, what: list[bytes | str], start_index=0):
		ret = len(line)
		for w in what:
			if (i := line.find(w, start_index)) >= 0 and i < ret:
				ret = i
		return ret

	ret = False
	if (line_index := get_section_line_index(section, value_name, open_fn=open_fn)):
		# read .ltx file to buffer
		with open_fn(section.ltx.ltx_file_path, 'rb') as f:
			buff = f.readlines()
		# write buffer to .ltx file
		with open_fn(section.ltx.ltx_file_path, 'wb') as f:
			for i, line in enumerate(buff):
				if i == line_index:
					# found .ltx file line with lvalue to update
					eq_index = line.find(b'=')
					end_index = find_in_line(line, (b';', b'\r', b'\n'), eq_index)
					line = bytearray(line)
					line[eq_index + 1:end_index] = (' ' + new_value.strip()).encode()
				f.write(line)
		return ret
	return ret

def update_section_values(section: Ltx.Section, values: dict[str, str], game: 'GameConfig') -> bool:
	'updates lvalues of .ltx file section'

	def find_in_line(line: str | bytes, what: list[bytes | str], start_index=0):
		ret = len(line)
		for w in what:
			if (i := line.find(w, start_index)) >= 0 and i < ret:
				ret = i
		return ret

	ret = False
	is_buffer_dirty = False
	localize_buff: dict[str, str] = {}  # id: text
	# get indexes of .ltx file lines for value names
	if (line_indexes := get_section_line_index(section, values.keys(), open_fn=game.paths.open)):
		# define .ltx files encoding in gamedata path
		encoding, line_separator = game.paths.get_gamedata_text_info()
		# read .ltx file to buffer
		if game.verbose:
			print(f'Edit [{section.name}] {section.ltx.ltx_file_path}')
		with game.paths.open(section.ltx.ltx_file_path, 'rb') as f:
			buff = f.readlines()
		# update .ltx buffer
		for i, line in enumerate(buff):
			if i in line_indexes.values():
				# found .ltx file line with lvalue to update
				new_value = values.get(next(k for k, v in line_indexes.items() if v == i))
				eq_index = line.find(b'=')
				end_index = find_in_line(line, (b';', b'\r', b'\n'), eq_index)
				line = bytearray(line)  # line: lvalue = rvalue
				# check is rvalue to replace is localized id
				if (rvalue := line[eq_index + 1:end_index]):  # rvalue to replace
					rvalue = rvalue.strip().decode(encoding)
					if rvalue == new_value:
						if game.verbose:
							print(f'\tnot changed {i}: {line[:eq_index].strip().decode(encoding)}={rvalue}')
						continue  # not changed # ignore new value
					# try treat rvalue as localize id
					if (localized := game.localize(rvalue, localized_only=True)):
						# is localization id
						if localized == new_value:
							if game.verbose:
								print(f'\tnot changed {i}: {line[:eq_index].strip().decode(encoding)}={rvalue} localized "{localized}"')
							continue  # not changed # ignore new value
						localize_buff[rvalue] = new_value  # use .xml localization buffer
						continue  # update of .xml localization file is buffered
					# replace rvalue in .ltx file # use .ltx file buffer
					line[eq_index + 1:end_index] = (' ' + new_value).encode(encoding)
					buff[i], is_buffer_dirty = line, True  # mark .ltx buffer to flush to file
		if is_buffer_dirty:
			# flush .ltx buffer to file
			with game.paths.open(section.ltx.ltx_file_path, 'wb') as f:
				f.write(line_separator.join((x.rstrip() for x in buff)))
		if localize_buff:
			# update .xml localization files
			game.localization.update_files(localize_buff, verbose=game.verbose)
		return ret
	return ret

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

		def edit_ask() -> bool | None:
			while True:
				anwer = input(f'edit file (y, N, s[kip file], e[xit]) to "{args.m}" ? : ')
				match anwer.strip():
					case 'y' | 'Y':
						return True
					case '' | 'n' | 'N':
						return False
					case 's' | 'S':
						return None
					case f as str if f.lower() in 'exit':
						from sys import exit; exit(0)

		for path_ in args.ltx:
			if isdir(path_):
				path_ = join(path_, '**/*.ltx')
			for path_ in glob(path_, recursive=True):
				lines_indexes = print_ltx_file(path_)
				if lines_indexes:
					# edit file
					# print(f'{lines_indexes=}')
					match edit_ask():
						case False:
							continue
						case None:
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

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
