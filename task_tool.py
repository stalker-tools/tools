#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker Xray game .ltx and .xml files tool for actor tasks
# Author: Stalker tools, 2023-2024

from sys import stderr
from os.path import basename
# tools imports
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from ltx_tool import parse_ltx_file, LtxKind
from localization import Localization


def get_tasks_ltx_file_path(paths: Paths) -> str | None:
	'returns path to task_manager.ltx file'
	# try find tasks .ltx file
	for ff in paths.find('*task_manager.ltx'):
		return ff
	return None

def get_tasks_and_add_localization(paths: Paths, verbose = True) -> dict[str, dict[str, object]] | None:
	if (ltx_file_path := get_tasks_ltx_file_path(paths)):
		sections, section = {}, {}
		prev_section_name = None
		for x in parse_ltx_file(ltx_file_path, follow_includes=True, open_fn=paths.open):
			match x:
				case (LtxKind.NEW_SECTION, section_name, section_parents):
					if section_name in sections:
						print(f'duplicated section name: {section_name}', file=stderr)
					if len(section) > 1:
						sections[prev_section_name] = section
					section = { '': section_parents }
					prev_section_name = section_name
				case (LtxKind.LET, _, _, lval, rvals):
					section[lval] = rvals if len(rvals) > 1 else rvals[0]
		if len(section) > 1:
			sections[prev_section_name] = section

		# add localization # find quest xml localization files
		# for localization_xml_file_path in glob(join(localization_text_path, 'st_quest*.xml')):
		# 	add_localization_dict_from_localization_xml_file(localization_dict, configs_path, localization_xml_file_path, verbose)

		return sections
	return None


if __name__ == '__main__':
	from sys import argv, exit
	import argparse
	from pathlib import Path

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray task_manager.ltx file parser.
Out formats: html table, csv table.

Note:
It is not necessary to extract .db/.xdb files to gamedata path. This utility can read all game files from .db/.xdb files !
''',
				epilog=f'''Examples:
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru --head "Clear Sky 1.5.10 tasks" > "tasks.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru --sort-field name --head "Clear Sky 1.5.10 tasks" > "tasks.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru --sort-field name -oc" > "tasks.csv"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', help='game root path (with .db/.xdb files); default: current path')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			parser.add_argument('-f', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata directory path; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('--exclude-gamedata', action='store_true', help='''exclude files from gamedata sub-path;
used to get original game (.db/.xdb files only) infographics; default: false
''')
			parser.add_argument('-v', action='store_true', help='increase information verbosity: show phrase id')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-o', '--output-format', metavar='OUT_FORMAT', default='h', help='output format: h - html table (default), c - csv table')
			parser.add_argument('--sort-field', metavar='NAME', default='name', help='sort field name: name (default)')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			return parser.parse_args()

		def analyse(gamedata_path: str):

			paths = Paths(gamedata_path)
			loc = Localization(paths, verbose=verbose)
			# localization_text_path = join(configs_path, 'text', args.localization)
			# localization_dict: dict[str, str] = {}  # localization string: id, text

			if args.output_format != 'c':
				print(f'<html>\n<head><title>{args.head}</title></head>')
				print(f'<body>')
				print(f'<h1>{args.head}</h1><hr/>')
				STYLE_TEXT_LEFT = 'style="text-align: left;"'

			tasks_sections_dict = get_tasks_and_add_localization(paths, args.output_format != 'c')

			def get_task_value(task: dict[str, object], value_name: str) -> str | None:
				if value_name in task:
					return task.get(value_name)
				# try find value in parents sections
				if (parents := task.get('')):
					for parent in parents:
						if (parent_task := tasks_sections_dict.get(parent)):
							if (value := get_task_value(parent_task, value_name)) is not None:
								return value
				return None

			LOCALIZED_TASK_VALUE_NAMES = ('name', 'text')
			TASK_FILTER_NAMES_WITH_NAME_SUBSORT = ('task_type', 'faction')

			def _get_section_value(task_id: str, task: dict[str, object], value_name: str) -> str | None:
				if value_name == 'id':
					return task_id
				if (value := get_task_value(task, value_name)):
					if value_name in LOCALIZED_TASK_VALUE_NAMES:
						# try get localization
						if (localized_value := loc.string_table.get(value)):
							return localized_value
						print(f'localization not found: {value}', file=stderr)
					return value
				return ''

			def _get_section_value_sort(task_id: str, task: dict[str, object], filter: str) -> str:
				if (value := _get_section_value(task_id, task, filter)):
					if filter in TASK_FILTER_NAMES_WITH_NAME_SUBSORT:
						return value + _get_section_value_sort(task_id, task, 'name')
					value = str(value).lstrip()
					return value if ord(value[0]) < 128 else ' ' + value
				if filter in TASK_FILTER_NAMES_WITH_NAME_SUBSORT:
					return _get_section_value_sort(task_id, task, 'name')
				return ''

			def add_section_value(task_id: str, task: dict[str, object], value_name: str, is_last = False):
				buff = _get_section_value(task_id, task, value_name)
				if args.output_format != 'c':
					if type(buff) is tuple:
						buff = '<br/>'.join(buff)
					if value_name == 'reward_item':
						buff = '<br/>'.join(buff.split(':'))
					if value_name in LOCALIZED_TASK_VALUE_NAMES:
						print(f'<th {STYLE_TEXT_LEFT}>{buff}</th>')
					else:
						print(f'<th>{buff}</th>')
				else:
					if type(buff) is tuple:
						buff = ','.join(buff)
					if type(buff) is str:
						if '"' in buff:
							buff = buff.replace('"', '\'')
						buff = '"' + buff + '"'
					print(buff, end='' if is_last else ',')

			FILELD_NAMES = ('No', 'Id', 'Name', 'Text', 'Task type', 'Faction', 'Reward money', 'Reward item')

			if args.output_format != 'c':
				print('<table border=1 style="border-collapse: collapse;">')
				print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead>')
				print('<tbody>')
			else:
				print(f'{",".join((x for x in FILELD_NAMES))}')
			if tasks_sections_dict:
				for index, task_id_and_values in enumerate(sorted(tasks_sections_dict.items(), key=lambda x:
						_get_section_value_sort(*x, args.sort_field))):
					match args.output_format:
						case 'h':
							print('<tr>')
							print(f'<th>{index + 1}</th>')
						case 'c':
							print(f'{index + 1}', end=',')
					add_section_value(*task_id_and_values, 'id')
					add_section_value(*task_id_and_values, 'name')
					add_section_value(*task_id_and_values, 'text')
					add_section_value(*task_id_and_values, 'task_type')
					add_section_value(*task_id_and_values, 'faction')
					add_section_value(*task_id_and_values, 'reward_money')
					add_section_value(*task_id_and_values, 'reward_item', True)
					print('</tr>' if args.output_format != 'c' else '')
			if args.output_format == 'h':
				print('</tbody></table>')
				print('</body>\n</html>')


		args = parse_args()
		verbose = args.v

		gamepath = Path(args.gamepath) if args.gamepath else Path()
		paths_config = None
		if gamepath:
			if not args.version:
				raise ValueError(f'Argument --version or -t is missing; see help: {argv[0]} -h')
			paths_config = PathsConfig(
				gamepath.absolute(), args.version,
				args.gamedata,
				verbose=verbose,
				exclude_gamedata=args.exclude_gamedata)
		analyse(paths_config)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
