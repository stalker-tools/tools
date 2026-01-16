#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker Xray game .xml localization files tool
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
from sys import stderr
from os.path import basename, join
from glob import glob
from xml.dom.minidom import Document
from pickle import load as pickle_load, dump as pickle_dump
# stalker-tools import
from ltx_tool import parse_ltx_file, LtxKind
from paths import Paths
from xml_tool import xml_parse, get_child_element_values, XmlParser


_STRINGS_ENTRY_TYPE = tuple[str, str, int, int]  # (string, xml file path, line no: 1.., line pos: 0..)


class Localization:
	'Localization strings by id. See dict string_table'

	def __init__(self, paths: Paths, verbose = 0, cache_file_path: str | None = None) -> None:
		self.verbose = verbose
		self.is_from_cache = False
		self.paths = paths
		if self.verbose:
			print(f'Gamedata path: "{self.paths}"')

		# load from cache
		if cache_file_path:
			try:
				with open(cache_file_path, 'rb') as f_cache:
					self.string_table_files, self.language, self.localization_text_path, self.string_table \
						= pickle_load(f_cache)
					self.is_from_cache = True
					if self.verbose:
						print(f'Load localization from cache: {cache_file_path}')
					return
			except FileNotFoundError: pass

		# find .ltx section string_table and define localization language and string_table .xml files names
		self.string_table_files, self.language = None, None  # config data
		self._load_string_table_ltx_section()
		self.localization_text_path = join(self.paths.configs, 'text', self.language) if self.language else None
		# find string_table .xml files
		self.string_table: dict[str, _STRINGS_ENTRY_TYPE] = {}  # localized strings: id, (string, xml file path, line no: 1.., line pos: 0..)
		self._load_string_tables()

	def save_cache(self, cache_file_path: str):
		if not self.is_from_cache:
			if self.verbose:
				print(f'Save localization to cache: {cache_file_path}')
			with open(cache_file_path, 'wb') as f_cache:
				pickle_dump(
					(self.string_table_files, self.language, self.localization_text_path, self.string_table),
					f_cache)

	def _load_string_table_ltx_section(self):
		'load localization parameters from .ltx string_table section included from system.ltx'
		try:
			for x in parse_ltx_file(self.paths.system_ltx, follow_includes=True, open_fn=self.paths.open):
				match x:
					case (LtxKind.LET, _, 'string_table', 'files', buff):
						self.string_table_files = buff
						if self.verbose:
							print(f'String_table .xml files: {self.string_table_files}')
						if self.language:
							return
					case (LtxKind.LET, _, 'string_table', 'language', buff):
						self.language = buff if type(buff) is str else buff[0]
						if self.verbose:
							print(f'Language: {self.language}')
						if self.string_table_files:
							return
		except Exception as e:
			pass

	def _load_string_tables(self):
		'load localized strings from .xml string_table files'
		if self.string_table_files and self.localization_text_path:
			for string_table_file in self.string_table_files:
				xml_file_name = join(self.localization_text_path, f'{string_table_file}.xml')
				if self.verbose:
					print(f'Parse string_table file {string_table_file}: "{xml_file_name}"')
				self.add_localization_xml_file(xml_file_name)

	def add_localization_xml(self, _xml: Document, xml_file_path: str) -> bool:
		'_xml - string_table document'

		def normalize_text(text: str) -> str:
			'replace escape sequence: new line'
			if text:
				while '\\n' in text:
					text = text.replace('\\n', '\n')
			return text

		ret = False

		for _string in _xml.getElementsByTagName('string'):
			if (string_id := _string.getAttribute('id')):
				self.string_table[string_id] = (normalize_text(get_child_element_values(_string, 'text', '\n')), xml_file_path)
				ret = True
		
		return ret

	def _iter_xml_file(self, file_path: str, *, low_level = False) -> Iterator[tuple[str, _STRINGS_ENTRY_TYPE] | XmlParser.Tag]:
		'iters localization id and entry'

		def normalize_text(text: str) -> str:
			'replace escape sequence: new line'
			if text:
				while '\\n' in text:
					text = text.replace('\\n', '\n')
			return text

		xml_parser = XmlParser(self.paths, file_path)
		file_path = None
		is_string_table, id = False, None
		for file_or_tag in xml_parser.parse():
			if isinstance(file_or_tag, str):
				# .xml file path
				file_path = file_or_tag
			else:
				# .xml file tag
				# file_or_tag: XmlParser.Tag = file_or_tag
				match file_or_tag.name:
					case b'string':
						# localized string with id
						if is_string_table:
							if (id := file_or_tag.get_attribute(b'id')):
								id = id
					case b'text':
						if id:
							if is_string_table and id and (value := file_or_tag.value):
								if low_level:
									yield (id, file_or_tag)
								else:
									yield (id, (normalize_text(value), file_path, file_or_tag.line_no, file_or_tag.line_pos))
							id = None
					case b'string_table':
						is_string_table = True

	def add_localization_xml_file(self, file_path: str):
		'add localization .xml file to localized strings with ids'

		for id, entry in self._iter_xml_file(file_path):
			self.string_table[id] = entry

		# try:
		# 	if (_xml := xml_parse(file_path, self.paths.configs, open_fn=self.paths.open)):
		# 		self.add_localization_xml(_xml, file_path)
		# except Exception as e:
		# 	if self.verbose:
		# 		print(f'Localization .xml file parse error: {file_path} {e}', file=stderr)

	def try_find_and_add(self, id: str, file_name_filter = 'st_dialog*.xml') -> bool:
		# try find not well-known .xml localization files

		def find_in_file(file_path: str, text: bytes) -> bool:
			with self.paths.open(file_path, 'rb') as f:
				is_localization_file = False
				for line in f.readlines():
					if line.strip() == b'<string_table>':
						is_localization_file = True
					elif is_localization_file and text in line:
						return True
			return False

		if id.startswith('GENERATE_NAME'):
			return False

		try:
			for file_path in glob(join(self.localization_text_path, file_name_filter)):
				if find_in_file(file_path, f'"{id}"'.encode()):
					# localization xml file found
					print(f'Localization found: {file_path[len(self.paths.gamedata) + 1:]}', file=stderr)
					self.add_localization_xml_file(file_path)
					return True
		except Exception as e:
			print(e)
			pass

		return False

	def get(self, id: str, case_insensitive=False, get_file_path = False) -> str | None:
		'returns localized str by id, or localize file path'
		if self.string_table:
			if (buff := self.string_table.get(id)):
				return buff[1] if get_file_path else buff[0]
			if case_insensitive:
				id = id.lower()
				for k, buff in self.string_table.items():
					if k.lower() == id:
						return buff[1] if get_file_path else buff[0]
		return None

	def update_file(self, id: str, new_value: str, case_insensitive=False) -> bool:
		'returns True if localized string by id was modified in .xml file'

		def replace_id_value(tag: XmlParser.Tag):
			'replaces tag inner value in .xml file with id'
			# load .xml file to modify
			with self.paths.open(file_path, 'br') as f:
				buff = bytearray(f.read())
			# define binary piece and modify it
			pos, len = tag.value_pos_and_len
			buff[pos:pos+len] = new_value.encode(tag.encoding)
			# write modified .xml file
			with self.paths.open(file_path, 'wb') as f:
				f.write(buff)

		# find .xml file path for localization id
		if (file_path := self.get(id, case_insensitive, True)):
			# parse current .xml file and find .xml tag with id
			for id_file, tag in self._iter_xml_file(file_path, low_level=True):
				if id == id_file:
					# id found # replace .xml tag inner value
					replace_id_value(tag)
					return True

		return False


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray localization tool',
				epilog=f'''Examples:
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-v', action='count', help='increase information verbosity: -v, -vv')
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			return parser.parse_args()

		args = parse_args()
		# print(args)
		loc = Localization(Paths(args.gamedata), args.v)
		if args.v:
			print(f'Language: {loc.language}')
			print(f'String table files: {loc.string_table_files}')
			print(f'Text path: {loc.localization_text_path}')
			print(f'String table:{"" if loc.string_table else " <None>"}')
		for k, v in loc.string_table.items():
			print(f'{k}={v}')

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
