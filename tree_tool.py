#!/usr/bin/env python3

from typing import NamedTuple
from os.path import join, basename, split
from base64 import b64encode
import pydot
from ltx_tool import parse_ltx_file, LtxKind, LtxFileNotFoundException


class NodeStyle(NamedTuple):
	shape: str = 'tripleoctagon'
	penwidth: int = 1
	color: str = 'black'
	color_missing: str = 'red'
	level_fontsize: tuple[str] = ('12pt', '7pt')
	def get_fontsize(self, level: int):
		return self.level_fontsize[level] if level < len(self.level_fontsize) else self.level_fontsize[-1]
	level_height: tuple[float] = (2, 1)
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


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray .ltx file parser. Out format: dot (default) and rendered dot embedded in html as image.\nUse different layout engines: https://www.graphviz.org/docs/layouts/',
				epilog=f'''Examples:
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky .ltx files tree" > "ltx_tree_cs.htm"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -ecirco --head "Clear Sky .ltx files tree" > "ltx_tree_cs.htm"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" > "ltx_tree_cs.dot"
{basename(argv[0])} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -sl > "ltx_tree_cs.dot"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-e', '--engine', metavar='ENGINE', default='neato', help='dot layout engine: circo, dot, neato (default)')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('--head', metavar='TEXT', help='head text for html output')
			return parser.parse_args()

		args = parse_args()

		def get_graph_as_html_img(graph) -> str:

			def get_dot_as_image(graph) -> bytes:
				return graph.create_png(prog=args.engine)

			return '<img src="data:;base64,{}"/>'.format(b64encode(get_dot_as_image(graph)).decode())

		def analyse(gamedata_path: str):

			def add_node(level, name: str, parent_name: str | None = None, label: str | None = None) -> tuple['Node', 'Edge | None']:
				node = pydot.Node(name, label=label if label else name, fontsize=style.node.get_fontsize(level), height=style.node.get_height(level),
					penwidth=style.node.penwidth, shape=style.node.shape, color=style.node.color, fontcolor=style.node.color)
				graph.add_node(node)

				if parent_name:
					edge = pydot.Edge(parent_name, name, penwidth=style.edge.penwidth, color=style.edge.color
						, minlen=10  # dot
						, len=8  # neato, fdp
						)
					graph.add_edge(edge)
					return node, edge

				return node, None

			def buid_ltx_include_tree(ltx_file_path, level=0, parent_name: str | None = None):
				# print(f'{ltx_file_path=} {parent_name=}')
				path = split(ltx_file_path)[0]
				ltx_path = join(configs_path, ltx_file_path)
				ltx_path_print = 'configs/' + ltx_file_path
				node, edge = add_node(level, ltx_path_print, parent_name)
				try:
					for x in parse_ltx_file(ltx_path):
						match x[0]:
							case LtxKind.INCLUDE:
								_, include_file_path = x[1], x[2]
								buid_ltx_include_tree(join(path, include_file_path), level + 1, ltx_path_print)
				except LtxFileNotFoundException:
					node.set_label(f'{node.get_label()} (missing)')
					node.set_color(style.node.color_missing)
					edge.set_color(style.node.color_missing)

			match args.style.lower():
				case 'l':
					style = LightStyle()
				case _:
					style = DarkStyle()

			graph = pydot.Dot('ltx files tree', graph_type='graph', bgcolor=style.bgcolor)
			graph.prog = args.engine
			# graph.set_dpi(64)
			graph.overlap_scaling = 0
			configs_path = join(gamedata_path, 'configs')
			buid_ltx_include_tree('system.ltx')

			if args.head:
				print(f'<h1>{args.head}<h1><hr/>')
				print(get_graph_as_html_img(graph))
			else:
				print(graph.create_dot().decode())

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
