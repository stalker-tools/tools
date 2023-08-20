#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import stderr
from typing import NamedTuple
from os.path import join, basename, split
from glob import glob
from base64 import b64encode
import pydot
from ltx_tool import parse_ltx_file, LtxKind, LtxFileNotFoundException, get_filters_re_compiled, is_filters_re_match
from xml.dom.minidom import parse as xml_parse, Element


class NodeStyle(NamedTuple):
	shape: str = 'box'
	shape_scenario: str = 'folder'
	shape_with_action: str = 'box3d'
	penwidth: int = 1
	color: str = 'black'
	color_missing: str = 'red'
	level_fontsize: tuple[str] = ('10pt', '7pt')
	def get_fontsize(self, level: int):
		return self.level_fontsize[level] if level < len(self.level_fontsize) else self.level_fontsize[-1]
	level_height: tuple[float] = (1, .5)
	def get_height(self, level: int):
		return self.level_height[level] if level < len(self.level_height) else self.level_height[-1]


class EdgeStyle(NamedTuple):
	color: str = 'black'
	penwidth: int = 1


class LightStyle(NamedTuple):
	bgcolor: str = 'white'
	node: NodeStyle = NodeStyle()
	edge: EdgeStyle = EdgeStyle()


class DarkStyle(NamedTuple):
	bgcolor: str = 'grey10'
	node: NodeStyle = NodeStyle(color='cornsilk2', color_missing='indianred2')
	edge: EdgeStyle = EdgeStyle(color='cornsilk2')


class GraphEngineNotSupported(Exception):
	def __init__(self, *args: object) -> None:
		super().__init__(*args)
		self.engine = args[0]
	def __str__(self) -> str:
		return self.engine


def iter_child_elements(element: Element):
	for e in (x for x in element.childNodes if type(x) == Element):
		yield e

def get_child_element_values(element: Element, child_name: str, join_str: str | None = None) -> list[str]:
	ret = []
	for e in element.getElementsByTagName(child_name):
		if (e := e.firstChild):
			ret.append(e.nodeValue)
	return join_str.join(ret) if join_str is not None else ret

def get_child_by_id(element: Element, child_name: str, id: str) -> Element | None:
	for e in element.getElementsByTagName(child_name):
		if (e_id := e.getAttribute('id')) and e_id == id:
			return e
	return None


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.\nOut format: html with dialog phrases digraphs embedded as images.\nUse different layout engines: https://www.graphviz.org/docs/layouts/',
				epilog=f'''Examples:
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 dialogs" > "dialogs.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -sl > "dialogs light theme.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -i "*hello*" "*barman*" --head "Clear Sky 1.5.10 dialogs" > "dialogs id hello or barman.html"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -p "*сигнал*" "*шрам*" --head "Clear Sky 1.5.10 dialogs" > "dialogs text filtered.html"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-v', action='store_true', help='increase information verbosity: show phrase id')
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-d', '--dialog-files', metavar='DIALOG_FILE', nargs='+', help='filter: dialog file names; see system.ltx [dialogs]')
			parser.add_argument('-i', '--dialog-ids', metavar='IDS', nargs='+', help='filter: dialogs ids; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml')
			parser.add_argument('-p', '--phrases', metavar='TEXT', nargs='+', help='filter: phrase text; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml')
			parser.add_argument('-e', '--engine', metavar='ENGINE', default='dot', help='dot layout engine: circo, dot (default), neato')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('--head', metavar='TEXT', default='S.T.A.L.K.E.R.', help='head text for html output')
			return parser.parse_args()

		args = parse_args()

		def get_graph_as_html_img(graph) -> str:

			def get_dot_as_image(graph) -> bytes:
				try:
					return graph.create_png(prog=args.engine)
				except FileNotFoundError:
					raise GraphEngineNotSupported(args.engine)

			return '<img src="data:;base64,{}"/>'.format(b64encode(get_dot_as_image(graph)).decode())

		def analyse(gamedata_path: str):

			match args.style.lower():
				case 'l':
					style = LightStyle()
				case _:
					style = DarkStyle()

			def get_dialogs(system_ltx_file_path: str) -> list[str] | None:
				try:
					for x in parse_ltx_file(system_ltx_file_path):
						match x:
							case (LtxKind.LET, _, 'dialogs', 'files', dialogs):
								return dialogs
				except LtxFileNotFoundException:
					pass
				return None

			def build_dialog_tree(dialog_xml_file_pah: str, text_xml_file_path: str):
				'''
				dialog_xml_file_pah - dialog xml: configs/gameplay/dialog*.xml
				text_xml_file_path - localization xml: configs/text/<LOCALIZATION>/st_dialog*.xml
				'''

				def create_dialog_graph(dialog: Element, string_table: Element | None) -> 'graph | None':
					'''
					dialog - dialog xml <dialog>
					string_table - localization xml <string_table>
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
						return smart_lines_split(ret)

					def add_graph_node(phrase: Element) -> bool:
						is_matched = not bool(phrases_patterns)
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
											label += f'{element.nodeName}={element.firstChild.nodeValue}\n'
										case _:
											if shape != style.node.shape_with_action:
												shape = style.node.shape_scenario
											label += f'{element.nodeName}={element.firstChild.nodeValue}\n'
								except:
									pass
							# add text to label and update text filter
							if (text := get_localized_text(get_child_element_values(phrase, 'text'))):
								if not is_matched:
									is_matched = is_filters_re_match(phrases_patterns, text)
								label += ('\n' if label else '') + text
							if not label:
								# show phrase id for empty phrases
								label = f'id={phrase_id}' + ('\n' if label else '') + label
							# create graph node and edges
							node = pydot.Node(phrase_id, label=label,
								fontsize=style.node.get_fontsize(0), height=style.node.get_height(0),
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

					graph = pydot.Dot('dialog tree', graph_type='digraph', bgcolor=style.bgcolor)
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
					with open(file_path, 'rb') as f:
						for line in f.readlines():
							if text in line:
								return True
					return False

				def get_localization_xml(text_xml_file_path: str) -> Element | None:
					try:
						return xml_parse(text_xml_file_path).getElementsByTagName('string_table')[0]
					except:
						return None

				def print_dialog_header():
					nonlocal print_xml_file_header
					if print_xml_file_header:
						print_xml_file_header = False
						print(f'<h2>{dialog_xml_file_pah[len(gamedata_path) + 1:]}<h2><hr/>')
					print(f'<h3>{dialogs_index + 1}	{dialog_id}<h3>')
					# print dialog xml elements
					for element in sorted(iter_child_elements(dialog), key=lambda element: element.nodeName):
						try:
							if element.nodeName != 'phrase_list':
								print(f'<small>{element.nodeName}={element.firstChild.nodeValue}</small><br/>')
						except:
							pass

				if (game_dialogs_list := xml_parse(dialog_xml_file_pah).getElementsByTagName('game_dialogs')):
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
											if (dialog_id := game_dialogs_list[0].getElementsByTagName('dialog')[0].getAttribute('id')):
												for file_path in glob(join(split(text_xml_file_path)[0], 'st_dialog*.xml')):
													if find_in_file(file_path, dialog_id.encode()):
														# localization xml file found
														string_table_list = get_localization_xml(file_path)
														print(f'<p>Localization: {file_path[len(gamedata_path) + 1:]}</p>')
														break
										except:
											pass
								if not phrases_patterns:
									print_dialog_header()
								if (graph := create_dialog_graph(dialog, string_table_list)) and graph.get_nodes():
									# phrases graph is not empty
									if phrases_patterns:
										print_dialog_header()
									print(get_graph_as_html_img(graph))
									# print(graph.create_dot().decode())

			configs_path = join(gamedata_path, 'configs')
			system_ltx_file_path = join(configs_path, 'system.ltx')
			text_path = join(configs_path, 'text', args.localization)
			dialogs = get_dialogs(system_ltx_file_path)

			dialog_ids_patterns = get_filters_re_compiled(args.dialog_ids)
			phrases_patterns = get_filters_re_compiled(args.phrases)

			if not dialogs:
				print(f'no dialogs in system.ltx: {system_ltx_file_path}', file=stderr)
				exit(-1)
			print(f'<html>\n<head><title>{args.head}</title></head>')
			print('<body>')
			print(f'<h1>{args.head}</h1>')
			dialogs = sorted(set(dialogs))
			if args.v:
				print(f'<p>system.ltx dialogs: {dialogs}</p>')
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
			for dialog in dialogs:
				build_dialog_tree(join(configs_path, 'gameplay', f'{dialog}.xml'), join(text_path, f'st_{dialog}.xml'))
			print('</body>\n</html>')

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
	except GraphEngineNotSupported as e:
		print(f'Graph engine not suppoted: {e}', file=stderr)
