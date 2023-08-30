#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import stderr
from os.path import join, basename
from glob import glob
from ltx_tool import parse_ltx_file, LtxKind
from xml_tool import xml_preprocessor, get_child_element_values
from xml.dom.minidom import Element
from xml_tool import add_localization_dict_from_localization_xml_file


def get_tasks_ltx_file_path(configs_path: str) -> str | None:
	'returns path to task_manager.ltx file'
	# try find tasks ltx file
	if (task_manager_file_path := glob(join(configs_path, '**', 'task_manager.ltx'), recursive=True)):
		return task_manager_file_path[0]
	return None

def get_tasks_and_add_localization(localization_dict: dict[str, str], configs_path: str, localization_text_path: str, verbose = True) -> dict[str, dict[str, object]] | None:
	if (ltx_file_path := get_tasks_ltx_file_path(configs_path)):
		sections, section = {}, {}
		prev_section_name = None
		for x in parse_ltx_file(ltx_file_path, follow_includes=True):
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
		for localization_xml_file_path in glob(join(localization_text_path, 'st_quest*.xml')):
			add_localization_dict_from_localization_xml_file(localization_dict, configs_path, localization_xml_file_path, verbose)

		return sections
	return None


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.\nOut format: html with dialog phrases digraphs embedded as images.\nUse different layout engines: https://www.graphviz.org/docs/layouts/',
				epilog=f'''Examples:
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 tasks" > "tasks.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name --head "Clear Sky 1.5.10 tasks" > "tasks.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name -oc" > "tasks.csv"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-v', action='store_true', help='increase information verbosity: show phrase id')
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-o', '--output-format', metavar='OUT_FORMAT', default='h', help='output format: h - html table (default), c - csv table')
			parser.add_argument('--sort-field', metavar='NAME', default='name', help='sort field name: name (default)')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			return parser.parse_args()

		args = parse_args()

		def analyse(gamedata_path: str):

			configs_path = join(gamedata_path, 'configs')
			localization_text_path = join(configs_path, 'text', args.localization)
			localization_dict: dict[str, str] = {}  # localization string: id, text

			if args.output_format != 'c':
				print(f'<html>\n<head><title>{args.head}</title></head>')
				print(f'<body>')
				print(f'<h1>{args.head}</h1><hr/>')
				STYLE_TEXT_LEFT = 'style="text-align: left;"'

			tasks_sections_dict = get_tasks_and_add_localization(localization_dict, configs_path, localization_text_path, args.output_format != 'c')

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
						if (localized_value := localization_dict.get(value)):
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

			def add_section_value(task_id: str, task: dict[str, object], value_name: str):
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
						buff = '"' + buff + '"'
					print(buff, end=',')

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
					add_section_value(*task_id_and_values, 'reward_item')
					print('</tr>' if args.output_format != 'c' else '')
			if args.output_format == 'h':
				print('</tbody></table>')
				print('</body>\n</html>')

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
