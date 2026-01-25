#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker Xray game .xml files tool
# Since .xml files break W3C XML rules
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
from sys import stderr
from io import BytesIO
from os import sep as path_separator
from os.path import join, basename, split
from xml.dom.minidom import parseString, Element, Document
# stalker-tools import
from paths import Paths


def xml_preprocessor(xml_file_path: str, include_base_path: str | None = None, included = False, failed_include_file_paths: list[str] = None,
		open_fn=open) -> bytes:
	'''features:
		- process #include to include text from another .xml files
		- removes comments <!-----> since they break W3C XML rules
		- removes <?xml tags in included documents since they break W3C XML rules
	'''

	buff = BytesIO()
	with open_fn(xml_file_path, 'rb') as f:
		for line in f.readlines():
			line_stripped = line.lstrip()
			if line_stripped.startswith(b'#include'):
				# include .xml file
				line_stripped = line_stripped[len(b'#include') + 1:].strip(b' \t\r\n').strip(b'"')
				line_stripped = line_stripped.replace(b'\\', path_separator.encode())  # convert path splitter to ext filesystem
				include_file_path = join(include_base_path if include_base_path else split(xml_file_path)[0], line_stripped.decode())
				try:
					buff.write(xml_preprocessor(include_file_path, include_base_path, True, open_fn=open_fn))
				except FileNotFoundError:
					if failed_include_file_paths is not None:
						if include_file_path in failed_include_file_paths:
							continue
						failed_include_file_paths.append(include_file_path)
					print(f'include file not found: {include_file_path}', file=stderr)
			elif line_stripped.startswith(b'<!--'):
				continue
			elif included and line.startswith(b'<?xml'):
				continue
			else:
				buff.write(line)
	return buff.getvalue()

def xml_parse(xml_file_path: str, include_base_path: str | None = None, included = False, failed_include_file_paths: list[str] = None,
		open_fn = open) -> Document:
	'''features:
		- process #include to include text from another .xml files
		- removes comments <!-----> since they break W3C XML rules
		- removes <?xml tags in included documents since they break W3C XML rules
	'''
	buff = xml_preprocessor(xml_file_path, include_base_path, included, failed_include_file_paths, open_fn=open_fn)
	return parseString(buff)

def iter_child_elements(element: Element):
	for e in (x for x in element.childNodes if type(x) == Element):
		yield e

def get_child_by_id(element: Element, child_name: str, id: str) -> Element | None:
	for e in element.getElementsByTagName(child_name):
		if (e_id := e.getAttribute('id')) and e_id == id:
			return e
	return None

def get_child_element_values(element: Element, child_name: str, join_str: str | None = None) -> list[str] | str:
	ret = []
	for e in element.getElementsByTagName(child_name):
		if (e := e.firstChild):
			ret.append(e.nodeValue)
	return join_str.join(ret) if join_str is not None else ret

def iter_lines(buff: bytes) -> Iterator[tuple[int, int, bytes]]:
	'''iters (line no: 1.., line position: 0.., line) with automatic detection of line delimiter
	buffer can be changed while iterating; used to edit iterated lines
	'''

	LINE_SEPS = b'\x0d\x0a'

	def define_line_seps(buff: bytes) -> bytes | None:
		ret = []
		line_sep_was_found = False
		for ch in buff:
			if ch in LINE_SEPS:
				line_sep_was_found = True
				ret.append(ch)
			elif line_sep_was_found:
				return bytes(ret)
		return None

	if (line_seps := define_line_seps(buff)):
		# it multiline text
		line_no, after_line_sep_index, line_seps_len = 1, 0, len(line_seps)
		while after_line_sep_index < len(buff):
			if (next_line_sep_index := buff.find(line_seps, after_line_sep_index)):
				if next_line_sep_index < 0:
					# last .xml line
					yield (line_no, after_line_sep_index, buff[after_line_sep_index:])
					break
				buff_len = len(buff)
				yield (line_no, after_line_sep_index, buff[after_line_sep_index:next_line_sep_index])
				if buff_len != len(buff):
					# buff lenght was changed
					next_line_sep_index += len(buff) - buff_len
				after_line_sep_index = next_line_sep_index + line_seps_len
				line_no += 1


class XmlParser:
	'''.xml files parser with source reflexion; special for X-ray: out-of-standard W3C XML
	used for localization files only for read and modify
	open/close tags in one line: tag name and all tag attributes in on line
	tag inner value in one line: tag open/close and inner value in one line; use \n for new line
	'''

	INCLUDE_DIRECTIVE = b'#include'
	DEFAULT_ENCODING = 'utf-8'


	class MissingCloseTag(Exception) : pass
	class AttributeExpected(Exception) : pass


	class Tag:
		'xml tag with attributes and inner value; tag editing facility is supported'

		__slots__ = ('buff', 'encoding', 'line_no', 'line_pos', '_is_buff_dirty')

		def __init__(self, buff: bytes, encoding: str, line_no: int, line_pos: int):
			self.buff, self.encoding = buff, encoding  # text with encoding
			self.line_no, self.line_pos = line_no, line_pos  # .xml file line: 1.., line absolute pos: 0..
			self._is_buff_dirty = False  # buffer was changed

		@property
		def name(self) -> bytes:
			'tag name'
			tag_open = self.buff.partition(b'>')[0]
			return tag_open.split(maxsplit=1)[0]

		def iter_attributes(self) -> Iterator[tuple[str, str]]:
			'iters tag attributes and their values'
			if (attributes := self.buff.split()):
				for attribute in attributes[1:]:
					attribute_name, _, attribute_value = attribute.partition(b'=')
					yield attribute_name, attribute_value[1:-1].decode(self.encoding)

		def get_attribute(self, name: bytes) -> str | None:
			'returns attribute value if any'
			for attribute_name, attribute_value in self.iter_attributes():
				if attribute_name == name:
					return attribute_value

		@property
		def value(self) -> str | None:
			'returns tag inner value'
			name = self.name
			if not (self.buff.startswith(name+b'>') and self.buff.endswith(b'</'+name)):
				raise self.MissingCloseTag(f'Close tag expected; file: {self.file_path}; line {self.line_no}: {self.buff}')
			if (value := self.buff[len(name)+1:-(len(name)+2)]):
				return value.decode(self.encoding)
			return None

		@property
		def value_pos_and_len(self) -> tuple[int, int]:
			'returns tag inner value pos: 0.., len: 0..'
			inner_pos = self.buff.find(b'>') + 1  # tag inner pos
			return (inner_pos, self.buff.rfind(b'</') - inner_pos)

		@property
		def value_absolute_pos_and_len(self) -> tuple[int, int]:
			'returns tag inner value for .xml file absolute pos: 0.., len: 0..'
			pos, len = self.value_pos_and_len
			return (self.line_pos + pos, len)

		def set_value(self, new_value: str):
			'sets tag inner value'
			# escape xml: &amp;
			new_value = new_value.replace('&', '&amp;')
			# replace file buffer with new value
			pos, len = self.value_pos_and_len
			if not isinstance(self.buff, bytearray):
				self.buff = bytearray(self.buff)
			self.buff[pos:pos+len] = new_value.encode(self.encoding)
			self._is_buff_dirty = True


	class FileBuffer:
		'buffered file read/write'

		def __init__(self, paths: Paths, file_path: str):
			self.paths = paths
			self.file_path = file_path
			self.is_dirty = False
			self.buff: bytearray | None = None
			self._read()

		def _read(self):
			with self.paths.open(self.file_path, 'rb') as f:
				if (buff := f.read()):
					self.buff = bytearray(buff)

		def save(self):
			if self.buff:
				with self.paths.open(self.file_path, 'wb') as f:
					f.write(self.buff)


	def __init__(self, paths: Paths, file_path: str):
		self.paths = paths
		self.file_path = file_path

	def _iter_lines(self, file_path: str) -> Iterator[tuple[int, int, bytes]]:
		'iters (line no: 1.., line position: 0.., line)'

		with self.paths.open(file_path, 'rb') as f:
			# load buffer from .xml file
			fb = self.FileBuffer(self.paths, file_path)
			if fb.buff:
				# process buffer line by line
				for v in iter_lines(fb.buff):
					yield fb, *v
				if fb.is_dirty:
					# buffer was changed # save buffer to .xml file
					fb.save()

	def parse(self) -> Iterator[str | Tag]:
		'''iters xml file with included xml files
		iters: str - new parsing .xml file path or Tag
		it loads xml file into memory
		'''

		def yield_tag():
			tag = self.Tag(line[1:-1], encoding, line_no, line_pos+offset+1)
			buff_len = len(tag.buff)
			yield (tag)
			if tag._is_buff_dirty:
				fb.buff[tag.line_pos:tag.line_pos+buff_len] = tag.buff
				fb.is_dirty = True

		def parse_include(file_path: str):
			yield file_path
			for fb, line_no, line_pos, _line in self._iter_lines(file_path):
				line = _line.strip()
				offset = _line.find(line)
				if line.startswith(b'<'):
					if not line.endswith(b'>'):
						# one-line tags supports only
						raise self.MissingCloseTag(f'Close tag expected; file: {file_path}; line {line_no}: {line}')
					yield from yield_tag()

		def get_encoding_from_tag(tag: str) -> str | None:
			'returns encoding name from <? ?> tag; tag without open/close symbols'
			for attribute_name, attribute_value in self.Tag(tag, encoding, 1, 0).iter_attributes():
				if attribute_name == b'encoding':
					return attribute_value
			return None

		yield self.file_path
		encoding = self.DEFAULT_ENCODING
		for fb, line_no, line_pos, _line in self._iter_lines(self.file_path):
			line = _line.strip()
			offset = _line.find(line)
			if line.startswith(b'</'):
				# closing tag
				pass
			elif line.startswith(self.INCLUDE_DIRECTIVE):
				# include .xml file; base path: config
				parse_include(self.paths.join(self.paths.configs, line[len(self.INCLUDE_DIRECTIVE)+1:].strip().strip(b'"').decode()))
			elif line.startswith(b'<?'):
				# get file encoding
				if not line.endswith(b'?>'):
					# one-line tags supports only
					raise self.MissingCloseTag(f'Close tag expected; file: {self.file_path}; line {line_no}: {line}')
				if (_encoding := get_encoding_from_tag(line[2:-2])):
					encoding_pref, _, encoding_number = _encoding.partition('-')
					if encoding_pref == 'windows':
						encoding = f'cp{encoding_number}'  # set encoding
			elif line.startswith(b'<'):
				if not line.endswith(b'>'):
					# one-line tags supports only
					raise self.MissingCloseTag(f'Close tag expected; file: {self.file_path}; line {line_no}: {line}')
				yield from yield_tag()


if __name__ == '__main__':
	import argparse
	from sys import argv, stdout

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray xml proprocessor. Features:
 - process #include to include text from another .xml files
 - removes comments <!-----> since they break W3C XML rules
 - removes <?xml tags in included documents since they break W3C XML rules''',
				epilog=f'''Examples:
{basename(argv[0])} "$HOME/.wine/drive_c/Program Files (x86)/Sigerous Mod/gamedata/configs/text/rus/SGM_add_include.xml" > "sgm_localization.xml"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-i', metavar='PATH', help='include base path')
			parser.add_argument('file', metavar='XML_FILE_PATH', help='.xml file to preprocess')
			return parser.parse_args()

		args = parse_args()

		stdout.buffer.write(xml_preprocessor(args.file, args.i))

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
