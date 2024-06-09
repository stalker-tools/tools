#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import stderr
from os.path import join, basename
from ltx_tool import parse_ltx_file, LtxKind
from xml.dom.minidom import parseString
from xml_tool import xml_preprocessor, get_child_element_values
from xml.dom.minidom import Element
# stalker-tools import
from dialog_tool import get_dialogs_and_add_localization, create_dialog_graph, get_svg, GraphEngineNotSupported, SvgException
from icon_tools import UiNpcUnique, UiIconstotal, get_image_as_html_img
from paths import Paths
from localization import Localization


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

def get_profiles_and_add_localization(paths: Paths, loc: Localization, verbose = False) -> dict[str, Element] | None:
	'return list[id, XML element]'
	files, specific_characters_files = get_profiles(paths.system_ltx)
	if not files:
		return None
	if verbose:
		print(f'<p><code>system.ltx profiles: {sorted(files)}</code></p>')
		if specific_characters_files:
			print(f'<p><code>system.ltx specific_characters_files: {sorted(specific_characters_files)}</code></p>')

	loc.add_localization_xml_file(join(loc.localization_text_path, 'st_characters.xml'))

	# ToDo: Add processing of .ltx [string_table] section

	specific_characters_dict = {}
	failed_include_file_paths = []
	for specific_characters_file in specific_characters_files:
		xml_file_path = join(paths.configs, 'gameplay', f'{specific_characters_file}.xml')
		try:
			buff = xml_preprocessor(xml_file_path, paths.configs, failed_include_file_paths=failed_include_file_paths)
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
			parser.add_argument('-o', '--output-format', metavar='OUT_FORMAT', default='h', help='output format: h - html table (default), d - html table + svg dialogs, c - csv table, b - brochure')
<<<<<<< HEAD
			parser.add_argument('--sort-field', metavar='NAME', default='name', help='sort field name: id, name (default), class, community, reputation, bio')
=======
			parser.add_argument('--sort-field', metavar='NAME', default='name', choices=('id', 'name', 'class', 'community', 'reputation', 'bio'), help='sort field name: id, name (default), class, community, reputation, bio')
>>>>>>> 3873aef (Add brochure format to profiles)
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			return parser.parse_args()

		args = parse_args()

		def _get_element_values(loc: Localization | None, element: Element, element_name: str) -> str | int:
			if element_name == 'id':
				return element.getAttribute('id')
			if (buff := get_child_element_values(element, element_name, '\n')):
				if loc:
					if (buff2 := loc.string_table.get(buff)):
						return buff2
					if element_name =='name':
						# enforce localization process
						if loc.try_find_and_add(buff):
							if (buff2 := loc.string_table.get(buff)):
								return buff2
				if element_name == 'reputation':
					try:
						return int(buff)
					except: pass
				return buff
			return ''

		def _get_element_values_sort(loc: Localization | None, element: Element, element_name: str):
<<<<<<< HEAD
			ret = _get_element_values(loc, element, element_name)
			match element_name:
				case 'name': return (ret if ord(ret[0]) < 128 else ' '+ret) + element.getAttribute('id')
				case 'reputation' | 'community' | 'bio': return ret + _get_element_values(element, 'name', True)
=======
			ret = _get_element_values(loc if element_name == 'name' else None, element, element_name)
			match element_name:
				case 'name': return (ret if ord(ret[0]) < 128 else ' '+ret) + element.getAttribute('id')
				case 'reputation': return f'{ret:05}{_get_element_values(loc, element, "name")}'
				case 'community' | 'bio': return ret + _get_element_values(loc, element, 'name')
>>>>>>> 3873aef (Add brochure format to profiles)
			return ret

		def analyse(gamedata_path: str):

			paths = Paths(gamedata_path)
			loc = Localization(paths)

			match args.style.lower():
				case 'l':
					from dialog_tool import LightStyle
					style = LightStyle()
				case _:
					from dialog_tool import DarkStyle
					style = DarkStyle()

			# print HTML header
			if args.output_format != 'c':
				print(f'<html>\n<head><title>{args.head}</title></head>')
				print(f'<body style="background-color:{style.page_bgcolor};color:{style.node.color};">')
				print(f'<h1>{args.head}</h1><hr/>')
			specific_characters_dict = get_profiles_and_add_localization(paths, loc, args.output_format != 'c')

			STYLE = 'style="text-align: left;"'

			def add_element_values(element_name: str, loc: Localization | None = None, is_last = False, convert = None):
				'print table cell from XML element'
				buff = _get_element_values(loc, specific_character, element_name)
				if args.output_format != 'c':
					print(f'<th {STYLE}>{convert(buff) if convert else buff}</th>')
				else:
					if type(buff) is str:
						if '"' in buff:
							buff = buff.replace('"', '\'')
						buff = '"' + buff + '"'
					print(buff, end='' if is_last else ',')

			def _create_dialog_graph(dialog_id: str):
				if (dialog := dialogs_dict.get(dialog_id)):
					if (graph := create_dialog_graph(dialog, args.engine, style, loc)):
						print(f'{dialog_id}:<br/>{get_svg(graph)}</br>')

			# get dialogs
			if args.output_format == 'd':
				dialogs_dict = get_dialogs_and_add_localization(paths, loc, args.output_format != 'c')

			FILELD_NAMES = ('No', 'Id', 'Name', 'Icon', 'Class', 'Community', 'Reputation', 'Bio')

			def print_table_header():
				if args.output_format != 'c':
					print('<table border=1 style="border-collapse: collapse;">')
					print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead>')
					print('<tbody>')
				else:
					print(f'{",".join((x for x in FILELD_NAMES))}')

			# print table header
			match args.output_format:
				case 'h' | 'c':
					print_table_header()
			# print table body
			if specific_characters_dict:

				def get_icon(id: str | None) -> str | None:
					if id and ui_npc_unique:
						if (image := ui_npc_unique.get_image(id)) or (image := ui_iconstotal.get_image(id)):
							return f'{id}<br/>{get_image_as_html_img(image)}'
					return id

				ui_npc_unique = UiNpcUnique(gamedata_path) if args.output_format != 'c' else None
				ui_iconstotal = UiIconstotal(gamedata_path) if args.output_format != 'c' else None

				for index, specific_character in enumerate(sorted(specific_characters_dict.values(), key=lambda x:
<<<<<<< HEAD
						_get_element_values_sort(loc if args.sort_field == 'name' else None, x, args.sort_field))):
=======
						_get_element_values_sort(loc, x, args.sort_field))):
>>>>>>> 3873aef (Add brochure format to profiles)
					match args.output_format:
						case 'h' | 'd':
							if args.output_format == 'd':
								print_table_header()
							print('<tr>')
							print(f'<th>{index + 1}</th>')
						case 'c':
							print(f'{index + 1}', end=',')
					add_element_values('id')
					add_element_values('name', loc)
					add_element_values('icon', convert=get_icon)
					add_element_values('class')
					add_element_values('community')
					add_element_values('reputation')
					add_element_values('bio', is_last=True)
					print('</tr>' if args.output_format != 'c' else '')
					if args.output_format == 'd':
						print('</tbody></table>')
						if (dialog_ids := get_child_element_values(specific_character, 'start_dialog')):
							for dialog_id in dialog_ids:
								_create_dialog_graph(dialog_id)
						if (dialog_ids := get_child_element_values(specific_character, 'actor_dialog')):
							for dialog_id in dialog_ids:
								_create_dialog_graph(dialog_id)
			# print HTML footer
			if args.output_format == 'h':
				print('</tbody></table>')
				print('</body>\n</html>')

		def brochure(gamedata_path: str, k_width = 1):
			paths = Paths(gamedata_path)
			loc = Localization(paths)
			specific_characters_dict = get_profiles_and_add_localization(paths, loc)

			def get_icon(id: str | None) -> str | None:
				if id and ui_npc_unique:
					if (image := ui_npc_unique.get_image(id)) or (image := ui_iconstotal.get_image(id)):
						return get_image_as_html_img(image)
				return id

			def get_money(specific_character: Element, prefix: str) -> str:
				if (money := specific_character.getElementsByTagName('money')) and (money := money[0]):
					_min, _max = money.getAttribute("min"), money.getAttribute("max")
					return f'{prefix}: {_min}{"..."+_max if _min != _max else ""}{"..." if money.getAttribute("infinitive") != "0" else ""}'
				return ''

			ui_npc_unique = UiNpcUnique(gamedata_path) if args.output_format != 'c' else None
			ui_iconstotal = UiIconstotal(gamedata_path) if args.output_format != 'c' else None
			print(f'<div style="display:grid;grid-template-columns:repeat(auto-fill,{int(375*k_width)}px);">')
			if specific_characters_dict:
				index = 1
				for specific_character in sorted(specific_characters_dict.values(), key=lambda x:
<<<<<<< HEAD
						_get_element_values_sort(loc if args.sort_field == 'name' else None, x, args.sort_field)):
=======
						_get_element_values_sort(loc, x, args.sort_field)):
>>>>>>> 3873aef (Add brochure format to profiles)
					name = _get_element_values(loc, specific_character, 'name')
					bio = _get_element_values(loc, specific_character, 'bio')
					if not name.startswith('GENERATE_NAME'):
						print(f'<div style="display:grid;padding:10px;margin:7px;border:1px outset;border-radius:15px;"><div style="display:flex;align-items:flex-start;">{index}&nbsp;&nbsp;&nbsp;<span style="font-weight:bold;font-size:larger;">{name}</span></div><div style="display:flex;align-items:flex-start;">{get_icon(_get_element_values(None, specific_character, "icon"))}<br/>&nbsp;Группировка: {_get_element_values(loc, specific_character, "community")}<br/>&nbsp;Ранг: {_get_element_values(loc, specific_character, "rank")}<br/>&nbsp;Репутация: {_get_element_values(loc, specific_character, "reputation")}<br/>&nbsp;{get_money(specific_character, "Деньги")}</div><div style="display:flex;align-items:end;">{bio}</div></div>')
						index += 1
			print('</div>')

		if args.output_format == 'b':
			brochure(args.gamedata)
		else:
			analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
	except GraphEngineNotSupported as e:
		print(f'Graph engine not suppoted: {e}', file=stderr)
	except SvgException as e:
		print(f'Svg error: {e}', file=stderr)
