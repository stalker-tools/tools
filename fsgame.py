#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fsgame.ltx parser
# Author: Stalker tools, 2023-2024

from os.path import abspath, dirname, join as pathjoin


class FormatException(Exception): pass


NameType = str
ValueType = str
FsgameType = dict[NameType, ValueType]


def parse(file_path: str) -> FsgameType | None:
	'returns fsgame.ltx parameters: dict[parameter, value]'
	ret, file_path = None, abspath(file_path)
	with open(file_path, 'r') as f:
		game_path = dirname(file_path)
		ret = {'fs_root': game_path}
		for line in (x for x in f.readlines() if x and x.startswith('$')):
			line = tuple(map(str.strip, line.split('|')))
			resource, _, _ = map(lambda x: x.strip(' \t'), line[0].partition('='))
			resource = resource.strip('$')
			if resource.lower() == 'app_data_root':
				if len(line) != 3:
					FormatException()
				ret[resource] = pathjoin(game_path, line[-1].rstrip('\\'))
			else:
				if len(line) == 4:
					ret[resource] = pathjoin(ret[line[-2].strip('$')], line[-1].rstrip('\\'))
				elif len(line) == 3:
					ret[resource] = ret[line[-1].strip('$')]
				else:
					FormatException()
	return ret


if __name__ == '__main__':
	from sys import argv
	import argparse

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='fsgame.ltx parser',
				epilog=f'Examples: {argv[0]} -f fsgame.ltx',
			)
			# parser.add_argument('-f', '--game', metavar='PATH', help='Game path')
			parser.add_argument('-f', '--file', metavar='PATH', required=True, help='fsgame.ltx file path')
			return parser.parse_args()

		# read command line arguments
		args = parse_args()

		fsgame = parse(args.file)

		# print paths
		max_len = max((len(x) for x in fsgame.keys()))
		for k, v in sorted(fsgame.items(), key=lambda x: x[0]):
			print(f'{k:{max_len+2}}{v}')

	main()
