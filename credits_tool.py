
from typing import Iterator, Callable
from pathlib import Path
# stalker-tools import
from xml_tool import xml_parse, XmlParser
from paths import Paths


def iter_tags(gamedata_path: str, file_path: str) -> Iterator[XmlParser.Tag]:
	paths = Paths(gamedata_path)
	xml_parser = XmlParser(paths, file_path)
	for file_or_tag in xml_parser.parse():
		if isinstance(file_or_tag, str):
			# .xml file path
			pass
		else:
			# .xml file tag
			yield file_or_tag


class Statistic:

	class Min:
		def __init__(self):
			self.value: int | None = None
		def set(self, val: int | None):
			if self.value is None or val < self.value:
				self.value = val
	class Max:
		def __init__(self):
			self.value: int | None = None
		def set(self, val: int | None):
			if self.value is None or val > self.value:
				self.value = val

	def __init__(self):
		self.min_x = Statistic.Min()
		self.min_y = Statistic.Min()
		self.max_x = Statistic.Max()
		self.max_y = Statistic.Max()
		self.min_width = Statistic.Min()
		self.max_width = Statistic.Max()
		self.min_height = Statistic.Min()
		self.max_height = Statistic.Max()
		self.min_start_time = Statistic.Min()
		self.max_start_time = Statistic.Max()

	def __repr__(self):
		return f'x={self.min_x.value}..{self.max_x.value}, y={self.min_y.value}..{self.max_y.value}, width={self.min_width.value}..{self.max_width.value}, height={self.min_height.value}..{self.max_height.value}, start_time={self.min_start_time.value}..{self.max_start_time.value}'

	def set_x(self, val: int | None):
		self.min_x.set(val)
		self.max_x.set(val)

	def set_y(self, val: int | None):
		self.min_y.set(val)
		self.max_y.set(val)

	def set_width(self, val: int | None):
		self.min_width.set(val)
		self.max_width.set(val)

	def set_height(self, val: int | None):
		self.min_height.set(val)
		self.max_height.set(val)

	def set_start_time(self, val: int | None):
		self.min_start_time.set(val)
		self.max_start_time.set(val)


def get_statistic(gamedata_path: str, file_path: str) -> Statistic:
	stat = Statistic()
	for tag in iter_tags(gamedata_path, file_path):
		if (x := tag.get_attribute(b'x')):
			x = int(x)
			stat.set_x(x)
		if (y := tag.get_attribute(b'y')):
			y = int(y)
			stat.set_y(y)
		if (width := tag.get_attribute(b'width')):
			width = int(width)
			stat.set_width(width)
		if (height := tag.get_attribute(b'height')):
			height = int(height)
			stat.set_height(height)
		if (start_time := tag.get_attribute(b'start_time')):
			start_time = int(start_time)
			stat.set_start_time(start_time)
	return stat

if __name__ == '__main__':
	import argparse
	from sys import argv, stdout
	from os.path import join, basename, split

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray xml credits parser. Used to gather text placement statistic.''',
				epilog=f'''Examples:
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" "config/ui/ui_credits_gsc.xml"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', help='game root path (with .db/.xdb files); default: current path')
			parser.add_argument('file', metavar='XML_FILE_PATH', help='credits .xml file')
			return parser.parse_args()

		args = parse_args()

		print('Statistic:')
		stat = get_statistic(join(args.gamepath, 'gamedata'), args.file)
		print(f'{stat}')

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
