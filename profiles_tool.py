#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import stderr
from os.path import join, basename
from ltx_tool import parse_ltx_file, LtxKind
from xml.dom.minidom import parseString
from xml_tool import xml_preprocessor, get_child_element_values
from xml.dom.minidom import Element
from dialog_tool import get_dialogs_and_add_localization, create_dialog_graph, get_svg, GraphEngineNotSupported, SvgException
from xml_tool import add_localization_dict_from_localization_xml_file


def get_profiles(system_ltx_file_path: str) -> tuple[list[str], list[str]] | tuple[None, None]:
	'returns files and specific_characters_files .xml from system.ltx includes: [profiles] files, specific_characters_files'
	files = specific_characters_files = None
	try:
		for x in parse_ltx_file(system_ltx_file_path, follow_includes=True):
			match x:
				case (LtxKind.LET, _, 'profiles', 'files', files):
					if files and specific_characters_files:
						return files, specific_characters_files
				case (LtxKind.LET, _, 'profiles', 'specific_characters_files', specific_characters_files):
					if files and specific_characters_files:
						return files, specific_characters_files
	except: pass
	return files, specific_characters_files

def get_profiles_and_add_localization(localization_dict: dict[str, str], configs_path: str, localization_text_path: str, system_ltx_file_path: str, verbose = False) -> dict[str, Element] | None:
	files, specific_characters_files = get_profiles(system_ltx_file_path)
	if not files:
		return None
	if verbose:
		print(f'<p><code>system.ltx profiles: {sorted(files)}</code></p>')
		if specific_characters_files:
			print(f'<p><code>system.ltx specific_characters_files: {sorted(specific_characters_files)}</code></p>')

	add_localization_dict_from_localization_xml_file(localization_dict, configs_path, join(localization_text_path, 'st_characters.xml'), verbose)

	specific_characters_dict = {}
	failed_include_file_paths = []
	for specific_characters_file in specific_characters_files:
		xml_file_path = join(configs_path, 'gameplay', f'{specific_characters_file}.xml')
		try:
			buff = xml_preprocessor(xml_file_path, configs_path, failed_include_file_paths=failed_include_file_paths)
		except FileNotFoundError:
			print(f'profile file not found: {xml_file_path}', file=stderr)
			continue
		if (_xml := parseString(buff)):
			specific_character_list = _xml.getElementsByTagName('specific_character')
			for specific_character in specific_character_list:
				specific_characters_dict[specific_character.getAttribute('id')] = specific_character

	return specific_characters_dict


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.\nOut format: html with dialog phrases digraphs embedded as images.\nUse different layout engines: https://www.graphviz.org/docs/layouts/',
				epilog=f'''Examples:
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 profiles" > "profiles.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -od -sl > "profiles with dialogs light theme.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name --head "Clear Sky 1.5.10 profiles" > "profiles.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name -oc" > "profiles.csv"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-v', action='store_true', help='increase information verbosity: show phrase id')
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-e', '--engine', metavar='ENGINE', default='dot', help='dot layout engine: circo, dot (default), neato')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('-o', '--output-format', metavar='OUT_FORMAT', default='h', help='output format: h - html table (default), d - html table + svg dialogs, c - csv table')
			parser.add_argument('--sort-field', metavar='NAME', default='id', help='sort field name: id (default), name, class, community, reputation, bio')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			return parser.parse_args()

		args = parse_args()

		def analyse(gamedata_path: str):

			configs_path = join(gamedata_path, 'configs')
			system_ltx_file_path = join(configs_path, 'system.ltx')
			localization_text_path = join(configs_path, 'text', args.localization)
			localization_dict: dict[str, str] = {}  # localization string: id, text

			match args.style.lower():
				case 'l':
					from dialog_tool import LightStyle
					style = LightStyle()
				case _:
					from dialog_tool import DarkStyle
					style = DarkStyle()

			if args.output_format != 'c':
				print(f'<html>\n<head><title>{args.head}</title></head>')
				print(f'<body style="background-color:{style.page_bgcolor};color:{style.node.color};">')
				print(f'<h1>{args.head}</h1><hr/>')
			specific_characters_dict = get_profiles_and_add_localization(localization_dict, configs_path, localization_text_path, system_ltx_file_path, args.output_format != 'c')

			STYLE = 'style="text-align: left;"'

			def _get_element_values(element: Element, element_name: str, use_localization = False):
				if element_name == 'id':
					return element.getAttribute('id')
				if (buff := get_child_element_values(element, element_name, '\n')):
					if use_localization:
						if (buff2 := localization_dict.get(buff)):
							return buff2
					if element_name == 'reputation':
						try:
							return int(buff)
						except: pass
					return buff
				return ''

			def _get_element_values_sort(element: Element, element_name: str, use_localization = False):
				ret = _get_element_values(element, element_name, use_localization)
				match element_name:
					case 'name': return ret + element.getAttribute('id')
					case 'reputation' | 'community' | 'bio': return ret + _get_element_values(element, 'name', True)
				return ret

			def add_element_values(element_name: str, use_localization = False):
				buff = _get_element_values(specific_character, element_name, use_localization)
				if args.output_format != 'c':
					print(f'<th {STYLE}>{buff}</th>')
				else:
					if type(buff) is str:
						buff = '"' + buff + '"'
					print(buff, end=',')

			def _create_dialog_graph(dialog_id: str):
				if (dialog := dialogs_dict.get(dialog_id)):
					if (graph := create_dialog_graph(dialog, args.engine, style, localization_dict)):
						print(f'{dialog_id}:<br/>{get_svg(graph)}</br>')

			if args.output_format == 'd':
				dialogs_dict = get_dialogs_and_add_localization(localization_dict, configs_path, localization_text_path, system_ltx_file_path, args.output_format != 'c')

			FILELD_NAMES = ('No', 'Id', 'Name', 'Class', 'Community', 'Reputation', 'Bio')

			def print_table_header():
				if args.output_format != 'c':
					print('<table border=1>')
					print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead>')
					print('<tbody>')
				else:
					print(f'{",".join((x for x in FILELD_NAMES))}')

			match args.output_format:
				case 'h' | 'c':
					print_table_header()
			if specific_characters_dict:
				for index, specific_character in enumerate(sorted(specific_characters_dict.values(), key=lambda x:
						_get_element_values_sort(x, args.sort_field, args.sort_field == 'name'))):
					match args.output_format:
						case 'h' | 'd':
							if args.output_format == 'd':
								print_table_header()
							print('<tr>')
							print(f'<th>{index + 1}</th>')
						case 'c':
							print(f'{index + 1}', end=',')
					add_element_values('id')
					add_element_values('name', True)
					add_element_values('class')
					add_element_values('community')
					add_element_values('reputation')
					add_element_values('bio')
					print('</tr>' if args.output_format != 'c' else '')
					if args.output_format == 'd':
						print('</tbody></table>')
						if (dialog_ids := get_child_element_values(specific_character, 'start_dialog')):
							for dialog_id in dialog_ids:
								_create_dialog_graph(dialog_id)
						if (dialog_ids := get_child_element_values(specific_character, 'actor_dialog')):
							for dialog_id in dialog_ids:
								_create_dialog_graph(dialog_id)
			if args.output_format == 'h':
				print('</tbody></table>')
				print('</body>\n</html>')

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
	except GraphEngineNotSupported as e:
		print(f'Graph engine not suppoted: {e}', file=stderr)
	except SvgException:
		print(f'Svg error', file=stderr)
