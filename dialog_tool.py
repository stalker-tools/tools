#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Stalker tools, 2023-2024


from sys import stderr
from typing import NamedTuple
from os.path import join, basename, split, sep
from glob import glob
from base64 import b64encode
import pydot
from xml.dom.minidom import Element
from xml.parsers.expat import ExpatError
# stalker-tools import
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from ltx_tool import parse_ltx_file, LtxKind, get_filters_re_compiled, is_filters_re_match
from xml_tool import iter_child_elements, get_child_by_id, get_child_element_values, xml_parse
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from localization import Localization


class NodeStyle(NamedTuple):
	shape: str = 'box'
	shape_scenario: str = 'folder'
	shape_with_action: str = 'box3d'
	fontname: str=''  #'serif'
	penwidth: int = 1
	color: str = 'black'
	color_missing: str = 'red'
	level_fontsize: tuple[str] = ('10', '7')
	def get_fontsize(self, level: int):
		return self.level_fontsize[level] if level < len(self.level_fontsize) else self.level_fontsize[-1]
	level_height: tuple[float] = (.7, .5)
	def get_height(self, level: int):
		return self.level_height[level] if level < len(self.level_height) else self.level_height[-1]


class EdgeStyle(NamedTuple):
	color: str = 'black'
	penwidth: int = 1


class LightStyle(NamedTuple):
	page_bgcolor: str = '#e8f1ec'
	bgcolor: str = '#e8f1ec40'
	node: NodeStyle = NodeStyle()
	edge: EdgeStyle = EdgeStyle()


class DarkStyle(NamedTuple):
	page_bgcolor: str = '#25252a'
	bgcolor: str = '#20202030'
	node: NodeStyle = NodeStyle(color='#c2c7c6', color_missing='indianred2')
	edge: EdgeStyle = EdgeStyle(color='#c2c7c6')


class GraphEngineNotSupported(Exception):
	def __init__(self, *args: object) -> None:
		super().__init__(*args)
		self.engine = args[0]
	def __str__(self) -> str:
		return self.engine


class SvgException(Exception):
	pass


def get_dialogs(system_ltx_file_path: str, open_fn = open) -> list[str] | None:
	'returns dialogs and additional localization .xml from system.ltx includes: [string_table] files'
	dialogs = None
	try:
		for x in parse_ltx_file(system_ltx_file_path, follow_includes=True, open_fn=open_fn):
			match x:
				case (LtxKind.LET, _, 'dialogs', 'files', dialogs):
					return dialogs				
	except:
		pass
	return dialogs

def get_dialogs_and_add_localization(paths: Paths, loc: Localization, verbose = False) -> dict[str, Element]:
	'returns tuple: dialog id and dialog xml element'

	def add_localization_for_dialog_file(dialog_xml_file_path: str, localization_xml_file_path: str):
		'adds localization ids and localization text for dialog xml file'

		def get_localization_xml(dialog_xml_file_path: str) -> Element | None:
			try:
				return xml_parse(dialog_xml_file_path, open_fn=paths.open).getElementsByTagName('string_table')[0]
			except ExpatError as e:
				print(f'XML file parse error: {dialog_xml_file_path} {e}', file=stderr)
				return None
			except:
				return None

		def find_in_file(file_path: str, text: bytes) -> bool:
			with paths.open(file_path, 'rb') as f:
				for line in f.readlines():
					if text in line:
						return True
			return False

		# add dialog to dialogs dict from dialogs .xml file
		try:
			test_dialog_id = None  # first dialog id from dialog .xml file
			for dialog in xml_parse(dialog_xml_file_path, open_fn=paths.open).getElementsByTagName('game_dialogs')[0].getElementsByTagName('dialog'):
				if (dialog_id := dialog.getAttribute('id')):
					dialogs_dict[dialog_id] = dialog
					if not test_dialog_id:
						test_dialog_id = dialog_id
		except ExpatError as e:
			print(f'Dialog .xml file error: {dialog_xml_file_path} {e}', file=stderr)
			return

		# try add localization for dialogs .xml file
		if test_dialog_id not in loc.string_table:
			# localization id not found # try add localization id
			if (_xml := get_localization_xml(localization_xml_file_path)):
				# localization .xml file found # add localization ids with localization text
				loc.add_localization_xml(_xml)
			else:
				# localization .xml file not found # try find xml file by text (any dialog id)
				# try find in well-known .xml files
				try:
					test_dialog_id = test_dialog_id.encode()
					for file_path in glob(join(loc.localization_text_path, 'st_dialog*.xml')):
						if find_in_file(file_path, test_dialog_id):
							# localization xml file found
							if (_xml := get_localization_xml(file_path)):
								loc.add_localization_xml(_xml)
								if verbose:
									print(f'<p><code>Localization: {file_path[len(split(paths.configs)[0]) + 1:]}</code></p>')
								break
				except:
					pass

	dialogs = get_dialogs(paths.system_ltx, open_fn=paths.open)
	dialogs_dict = {}
	for dialog in dialogs:
		add_localization_for_dialog_file(join(paths.configs, 'gameplay', f'{dialog}.xml'), join(loc.localization_text_path, f'st_{dialog}.xml'))
	return dialogs_dict

def create_dialog_graph(dialog: Element, engine: str, style: DarkStyle, loc: Localization, verbose = False, phrases_patterns = None, automation_patterns = None) -> 'graph':

	def get_localized_text(ids: list[str]) -> str:

		def smart_lines_split(text: str) -> str:
			LINE_LEN, LINE_DIFF = 90, 30
			SPLITTERS = ('...', '..', '?!', '!', '?', ' -', '.', ',', ' ')

			if text:
				ret = ''
				while len(text) > LINE_LEN + LINE_DIFF:
					for i, splitter in enumerate(SPLITTERS):
						if (split_index := text.find(splitter, LINE_LEN - LINE_DIFF)) > 0 and split_index < LINE_LEN + LINE_DIFF:
							ret += text[:split_index + len(splitter)] + '\n'
							text = text[split_index + len(splitter):].lstrip()
							break
						elif i == len(SPLITTERS) - 1:
							# last splitter not found # split anyway
							ret += text[:LINE_LEN + LINE_DIFF] + '\n'
							text = text[LINE_LEN + LINE_DIFF:]
							break
				if ret:
					return ret + text + '\n'
			return text

		ret = ''
		for id in ids:
			if (text := loc.get(id)):
				ret += text
		return smart_lines_split(ret)

	def add_graph_node(phrase: Element) -> bool:
		is_matched = not bool(phrases_patterns) and not bool(automation_patterns)
		if (phrase_id := phrase.getAttribute('id')):
			label, shape = f'id={phrase_id}\n' if verbose else '', style.node.shape
			# add to label all phrase xml elements except text and graph edges
			for element in sorted(iter_child_elements(phrase), key=lambda element: element.nodeName):
				try:
					match element.nodeName:
						case 'text' | 'next':
							pass
						case 'action':
							shape = style.node.shape_with_action
							nodeValue = element.firstChild.nodeValue
							label += f'{element.nodeName}={nodeValue}\n'
							if automation_patterns and not is_matched:
								is_matched = is_filters_re_match(automation_patterns, nodeValue)
						case _:
							if shape != style.node.shape_with_action:
								shape = style.node.shape_scenario
							nodeValue = element.firstChild.nodeValue
							label += f'{element.nodeName}={nodeValue}\n'
							if automation_patterns and not is_matched:
								is_matched = is_filters_re_match(automation_patterns, nodeValue)
				except:
					pass
			# add text to label and update text filter
			if (text := get_localized_text(get_child_element_values(phrase, 'text'))):
				if phrases_patterns and not is_matched:
					is_matched = is_filters_re_match(phrases_patterns, text)
				label += ('\n' if label else '') + text
			if not label:
				# show phrase id for empty phrases
				label = f'id={phrase_id}' + ('\n' if label else '') + label
			# create graph node and edges
			node = pydot.Node(phrase_id, label=label,
				fontsize=style.node.get_fontsize(0), height=style.node.get_height(0), fontname=style.node.fontname,
				penwidth=style.node.penwidth, shape=shape if phrase_id != '0' else 'oval', color=style.node.color, fontcolor=style.node.color)
			graph.add_node(node)
			if (next_ids := get_child_element_values(phrase, 'next')):
				for next_id in next_ids:
					edge = pydot.Edge(src=phrase_id, dst=next_id, penwidth=style.edge.penwidth, color=style.edge.color
						, minlen=1  # dot
						, len=5  # neato, fdp
						)
					graph.add_edge(edge)
		else:
			print('<p>No id for phrase</p>')
		return is_matched

	if (dialog_id := dialog.getAttribute('id')):
		graph = pydot.Dot(dialog_id, graph_type='digraph', bgcolor=style.bgcolor)
		graph.prog = engine
		graph.overlap_scaling = 0
		# graph.set_dpi(64)

		is_matched = False
		for phrase_list in dialog.getElementsByTagName('phrase_list'):
			for phrase in phrase_list.getElementsByTagName('phrase'):
				if add_graph_node(phrase):
					is_matched = True

		return graph if is_matched else None

def get_svg(graph) -> str:
	try:
		return graph.create_svg().decode()
	except Exception as e:
		raise SvgException(e)


if __name__ == '__main__':
	from sys import argv, exit
	import argparse
	from pathlib import Path

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.
Out format: html with dialog phrases digraphs embedded as svg or images.
In case of svg - dialogue phrases is text searchable: just open .html and use text search.
Use different layout engines, see: https://www.graphviz.org/docs/layouts/

Note:
It is not necessary to extract .db/.xdb files to gamedata path. This utility can read all game files from .db/.xdb files !
''',
				epilog=f'''Examples:
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru --head "Clear Sky 1.5.10 dialogs" > "dialogs.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru -sl > "dialogs light theme.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru -i "*hello*" "*barman*" --head "Clear Sky 1.5.10 dialogs" > "dialogs id hello or barman.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru -p "*сигнал*" "*шрам*" --head "Clear Sky 1.5.10 dialogs" > "dialogs text filtered.html"
{basename(argv[0])} -g ".../S.T.A.L.K.E.R" -t 2947ru -a "*not_in_dolg" "agru_open_story_door" --head "Clear Sky 1.5.10 dialogs" > "dialogs variable and function names filtered.html"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', help='game root path (with .db/.xdb files); default: current path')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('--exclude-gamedata', action='store_true', help='''exclude files from gamedata sub-path;
used to get original game (.db/.xdb files only) infographics; default: false
''')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			parser.add_argument('-f', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata directory path; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus',
				help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-d', '--dialog-files', metavar='DIALOG_FILE', nargs='+', help='filter: dialog file names; see system.ltx [dialogs]')
			parser.add_argument('-i', '--dialog-ids', metavar='IDS', nargs='+',
				help='filter: dialogs ids; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml')
			parser.add_argument('-p', '--phrases', metavar='TEXT', nargs='+',
				help='filter: phrase text; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml')
			parser.add_argument('-a', '--automation', metavar='NAMES', nargs='+',
				help='filter of names: variables, script functions; regexp, escaped symbols: ^$()[]?!')
			parser.add_argument('-e', '--engine', metavar='ENGINE', default='dot', help='dot layout engine: circo, dot (default), neato')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('--graph-format', metavar='IMG_FORMAT', default='s', help='digraph image format: s - svg (default), p - png')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; shows phrase id; examples: -v, -vv')
			return parser.parse_args()

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

		def get_graph_as_html_img(graph) -> str:

			def get_dot_as_image(graph) -> bytes:
				try:
					return graph.create_png(prog=args.engine)
				except FileNotFoundError:
					raise GraphEngineNotSupported(args.engine)

			if args.graph_format.lower() == 's':
				try:
					return graph.create_svg().decode()
				except:
					raise SvgException
			return '<img src="data:;base64,{}"/>'.format(b64encode(get_dot_as_image(graph)).decode())

		def analyse(paths: Paths):

			def build_dialog_tree(dialog_xml_file_pah: str, text_xml_file_path: str):
				'''
				dialog_xml_file_pah - dialog xml: configs/gameplay/dialog*.xml
				text_xml_file_path - localization xml: configs/text/<LOCALIZATION>/st_dialog*.xml
				'''

				def create_dialog_graph(dialog: Element, string_table: Element | None) -> 'graph | None':
					'''
					dialog - dialog xml <dialog>
					string_table - localization xml <string_table>

					Used: additional_string_table_xml - additional localization .xml from system.ltx includes
					'''

					def get_localized_text(ids: list[str]) -> str:

						def smart_lines_split(text: str) -> str:
							LINE_LEN, LINE_DIFF = 90, 30
							SPLITTERS = ('...', '..', '?!', '!', '?', ' -', '.', ',', ' ')

							if text:
								ret = ''
								while len(text) > LINE_LEN + LINE_DIFF:
									for i, splitter in enumerate(SPLITTERS):
										if (split_index := text.find(splitter, LINE_LEN - LINE_DIFF)) > 0 and split_index < LINE_LEN + LINE_DIFF:
											ret += text[:split_index + len(splitter)] + '\n'
											text = text[split_index + len(splitter):].lstrip()
											break
										elif i == len(SPLITTERS) - 1:
											# last splitter not found # split anyway
											ret += text[:LINE_LEN + LINE_DIFF] + '\n'
											text = text[LINE_LEN + LINE_DIFF:]
											break
								if ret:
									return ret + text + '\n'
							return text

						ret = ''
						if string_table:
							for id in ids:
								if id and (e := get_child_by_id(string_table, 'string', id)):
									ret += get_child_element_values(e, 'text', '\n')
						elif loc.string_table:
							# try find ids in localization string_table
							ret = '\n'.join(map(lambda id: loc.get(id) or '', ids))
						return smart_lines_split(ret)

					def add_graph_node(phrase: Element) -> bool:
						is_matched = not bool(phrases_patterns) and not bool(automation_patterns)
						if (phrase_id := phrase.getAttribute('id')):
							label, shape = f'id={phrase_id}\n' if args.v else '', style.node.shape
							# add to label all phrase xml elements except text and graph edges
							for element in sorted(iter_child_elements(phrase), key=lambda element: element.nodeName):
								try:
									match element.nodeName:
										case 'text' | 'next':
											pass
										case 'action':
											shape = style.node.shape_with_action
											nodeValue = element.firstChild.nodeValue
											label += f'{element.nodeName}={nodeValue}\n'
											if automation_patterns and not is_matched:
												is_matched = is_filters_re_match(automation_patterns, nodeValue)
										case _:
											if shape != style.node.shape_with_action:
												shape = style.node.shape_scenario
											nodeValue = element.firstChild.nodeValue
											label += f'{element.nodeName}={nodeValue}\n'
											if automation_patterns and not is_matched:
												is_matched = is_filters_re_match(automation_patterns, nodeValue)
								except:
									pass
							# add text to label and update text filter
							if (text := get_localized_text(get_child_element_values(phrase, 'text'))):
								if phrases_patterns and not is_matched:
									is_matched = is_filters_re_match(phrases_patterns, text)
								label += ('\n' if label else '') + text
							if not label:
								# show phrase id for empty phrases
								label = f'id={phrase_id}' + ('\n' if label else '') + label
							# create graph node and edges
							node = pydot.Node(phrase_id, label=label,
								fontsize=style.node.get_fontsize(0), height=style.node.get_height(0), fontname=style.node.fontname,
								penwidth=style.node.penwidth, shape=shape if phrase_id != '0' else 'oval', color=style.node.color, fontcolor=style.node.color)
							graph.add_node(node)
							if (next_ids := get_child_element_values(phrase, 'next')):
								for next_id in next_ids:
									edge = pydot.Edge(src=phrase_id, dst=next_id, penwidth=style.edge.penwidth, color=style.edge.color
										, minlen=1  # dot
										, len=5  # neato, fdp
										)
									graph.add_edge(edge)
						else:
							print('<p>No id for phrase</p>')
						return is_matched

					graph = pydot.Dot(dialog_id, graph_type='digraph', bgcolor=style.bgcolor)
					graph.prog = args.engine
					graph.overlap_scaling = 0
					# graph.set_dpi(64)

					is_matched = False
					for phrase_list in dialog.getElementsByTagName('phrase_list'):
						for phrase in phrase_list.getElementsByTagName('phrase'):
							if add_graph_node(phrase):
								is_matched = True

					return graph if is_matched else None

				def find_in_file(file_path: str, text: bytes) -> bool:
					with paths.open(file_path, 'rb') as f:
						for line in f.readlines():
							if text in line:
								return True
					return False

				def get_localization_xml(text_xml_file_path: str) -> Element | None:
					try:
						return xml_parse(text_xml_file_path, open_fn=paths.open).getElementsByTagName('string_table')[0]
					except ExpatError as e:
						print(f'XML file parse error: {text_xml_file_path} {e}', file=stderr)
						return None
					except:
						return None

				def print_dialog_header():
					nonlocal print_xml_file_header
					if print_xml_file_header:
						print_xml_file_header = False
						xml_file_name = dialog_xml_file_pah[len(str(paths.path)) + (0 if str(paths.path)[-1] == sep else 1):]
						print(f'<h2 id="{xml_file_name}">{xml_file_name}<h2><hr/>')
						if not string_table_list:
							print(f'<p><code>No localization found. Expected: {text_xml_file_path[len(str(paths.path)) + (0 if str(paths.path)[-1] == sep else 1):]}</code></p>')
					print(f'<h3 id="{dialog_id}">{dialogs_index + 1}	{dialog_id}<h3>')
					# print dialog xml elements
					for element in sorted(iter_child_elements(dialog), key=lambda element: element.nodeName):
						try:
							if element.nodeName != 'phrase_list':
								print(f'<code>{element.nodeName}={element.firstChild.nodeValue}</code><br/>')
						except:
							pass

				try:
					game_dialogs_list = xml_parse(dialog_xml_file_pah, open_fn=paths.open).getElementsByTagName('game_dialogs')
				except ExpatError as e:
					print(f'XML file parse error: {dialog_xml_file_pah} {e}', file=stderr)
					game_dialogs_list = None

				if game_dialogs_list:
					find_localization = True
					print_xml_file_header = True  # show xml file header for filtered dialogs only
					for game_dialogs in game_dialogs_list:
						for dialogs_index, dialog in enumerate(sorted(iter_child_elements(game_dialogs), key=lambda element: element.getAttribute('id'))):
							if (dialog_id := dialog.getAttribute('id')):
								if not is_filters_re_match(dialog_ids_patterns, dialog.getAttribute('id')):
									continue  # filter by dialog id
								if find_localization:
									find_localization = False
									# try find localization xml file
									string_table_list = get_localization_xml(text_xml_file_path)
									if not string_table_list:
										# localization xml file not found # try find xml file by text (any dialog id)
										try:
											dialog_id = game_dialogs_list[0].getElementsByTagName('dialog')[0].getAttribute('id')
										except:
											pass
										if dialog_id:
											localization_xml_path = split(text_xml_file_path)[0]
											# try find not well-known .xml files
											try:
												for file_path in glob(join(localization_xml_path, 'st_dialog*.xml')):
													if find_in_file(file_path, dialog_id.encode()):
														# localization xml file found
														string_table_list = get_localization_xml(file_path)
														print(f'<p>Localization: {file_path[len(str(paths.path)) + 1:]}</p>')
														break
											except:
												pass
								if not (phrases_patterns or automation_patterns):
									print_dialog_header()
								if (graph := create_dialog_graph(dialog, string_table_list)) and graph.get_nodes():
									# phrases graph is not empty
									if phrases_patterns or automation_patterns:
										print_dialog_header()
									print(get_graph_as_html_img(graph))
									# print(graph.create_dot().decode())

			configs_path, system_ltx_file_path = paths.configs, paths.system_ltx
			localization_text_path = join(configs_path, 'text', args.localization)
			dialogs = get_dialogs(system_ltx_file_path, open_fn=paths.open)
			loc = Localization(paths)

			dialog_ids_patterns = get_filters_re_compiled(args.dialog_ids)
			phrases_patterns = get_filters_re_compiled(args.phrases)
			automation_patterns = get_filters_re_compiled(args.automation)

			if not dialogs:
				print(f'no dialogs in system.ltx: {system_ltx_file_path}', file=stderr)
				exit(-1)

			match args.style.lower():
				case 'l':
					style = LightStyle()
				case _:
					style = DarkStyle()

			print(f'<html>\n<head><title>{args.head}</title></head>')
			print(f'<body style="background-color:{style.page_bgcolor};color:{style.node.color};">')
			print(f'<h1>{args.head}</h1>')
			dialogs = sorted(set(dialogs))
			if args.v:
				print(f'<p><code>system.ltx dialogs: {dialogs}</code></p>')
			if loc.string_table_files:
				print(f'<p><code>additional localization string_tables: {", ".join(loc.string_table_files)}</code></p>')
			if args.dialog_files:
				# filter dialogs files
				dialogs = set(dialogs).intersection(set(args.dialog_files))
				if not dialogs:
					print(f'no such dialogs filter: {args.dialogs}', file=stderr)
					exit(-1)
				print(f'<p>system.ltx filtered dialogs: {dialogs}</p>')
			if dialog_ids_patterns:
				print(f'<p>Filtered dialog ids: {args.dialog_ids}</p>')
			if phrases_patterns:
				print(f'<p>Filtered phrases: {args.phrases}</p>')
			if automation_patterns:
				print(f'<p>Filtered automation names: {args.automation}</p>')
			for dialog in dialogs:
				print(f'<a href="#{dialog}">{dialog}</a>')
			for dialog in dialogs:
				print(f'<p id="{dialog}"></p>')
				build_dialog_tree(join(configs_path, 'gameplay', f'{dialog}.xml'), join(localization_text_path, f'st_{dialog}.xml'))
			print('</body>\n</html>')

		paths = Paths(paths_config)
		analyse(paths)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
	except GraphEngineNotSupported as e:
		print(f'Graph engine not suppoted: {e}', file=stderr)
	except SvgException:
		print(f'Svg error', file=stderr)
