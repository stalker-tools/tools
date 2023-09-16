#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Iterator
from typing import NamedTuple
from io import BytesIO
from base64 import b64encode
from ltx_tool import Ltx
from game import Game

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():


		class GraphParams(NamedTuple):
			value_name: str
			value_label: str
			log_axies: bool = False


		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray .ltx file parser. Out format: matplotlib graphs embedded in html as images',
				epilog=f'Examples: {argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky - NPC and weapons" > "NPC_and_weapons.htm"',
			)
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('--head', default='S.T.A.L.K.E.R.', metavar='TEXT', help='head text')
			return parser.parse_args()

		args = parse_args()

		def analyse(gamedata_path: str):

			def get_float_value(value: str | tuple[str]) -> float:
				if value:
					value = value[0] if type(value) is tuple else value
					value = value.replace(' ', '')
					return float(value)
				return 0

			def get_value(text: str, type_=float) -> 'type_ | None':
				try:
					return type_(text)
				except:
					return None

			def remove_prefix(name: str, prefix: str) -> str:
				return name[len(prefix):] if name.startswith(prefix) else name

			def print_table(table: list[tuple[str]]):
				FILELD_NAMES = ('No', 'Section name', 'Name', 'Description')
				STYLE = 'style="text-align: left;"'
				print(f'<table border=1 style="border-collapse: collapse;">')
				print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead><tbody>')
				for index, field in enumerate(table):
					print('<tr>')
					print(f'<th>{index + 1}</th>')
					print(f'<th {STYLE}>{field[0]}</th>')
					print(f'<th>{field[1]}</th>')
					print(f'<th {STYLE}>{field[2]}</th>')
					print('</tr>')
				print(f'</tbody></table><p/>')

			def print_graphs(sections: list[Ltx.Section], graphs_params: list[GraphParams], group_name_index=0, width_k=None):
				# graphs_params = sorted(graphs_params, key=lambda x: x.value_name)
				sections = sections[::-1]
				sections_names = tuple(section.name for section in sections)
				fig = make_subplots(rows=1, cols=len(graphs_params), subplot_titles=tuple(x.value_name for x in graphs_params), horizontal_spacing=.08/len(graphs_params))
				bar_width, bgcolor = .6, 'rgba(50,50,50,28)'

				def get_colors(names: tuple[str]) -> tuple[str]:
					cycle_colors = pio.templates[pio.templates.default].layout.colorway
					cycle_colors_index = 0
					ret = []
					for i, name in enumerate(names):
						buff = name.split('_', group_name_index + 1)[group_name_index]
						if i > 0:
							if prev != buff:
								cycle_colors_index = (cycle_colors_index + 1) % len(cycle_colors)
						ret.append(cycle_colors[cycle_colors_index])
						prev = buff
					return ret

				colors = get_colors(sections_names)
				sections_names = tuple(f'{x} {len(sections_names)-i}' for i, x in enumerate(sections_names))
				for index, graphs_param in enumerate(graphs_params):
					values = tuple(get_float_value(section.get(graphs_param.value_name)) for section in sections)
					fig.append_trace(
						go.Bar(x=values, y=sections_names, orientation='h', width=bar_width, marker={'color': colors}),
						row=1, col=index + 1)
					fig.update_xaxes(title=graphs_param.value_label, col=index + 1)
					if graphs_param.log_axies:
						fig.update_xaxes(type='log')
				
				fig.update_layout(autosize=False, height=50 + len(sections) * 25, width=(175 + 160 * len(graphs_params)) * (width_k if width_k else 1),
					bargap=.01, bargroupgap=.01,
					margin={'l': 5, 'r': 5, 't': 30, 'b': 5}, showlegend=False, barmode='group', paper_bgcolor=bgcolor, plot_bgcolor=bgcolor)
				fig.update_xaxes(showgrid=True, showline=True, linewidth=2, griddash='dash', gridcolor='black')
				for trace_index in range(2, len(fig.data) + 1):
					fig.update_yaxes(visible=False, col=trace_index)

				print(fig.to_image('svg').decode())

			def get_table(iter_sections: Iterator[Ltx.Section], exclude_prefixes: list[str] = None):
				'exclude_prefixes - filter by section name (name prefix or entire name)'
				sections = []
				table: list[tuple[str]] = []
				prev_description = None
				# get ltx sections
				for section in sorted((x for x in iter_sections()), key=lambda section: section.name):
					if exclude_prefixes and any(section.name.startswith(x) for x in exclude_prefixes):
						continue
					if (inv_name_short := game.localize(section.get('inv_name_short'))):
						sections.append(section)
						description = section.get("description")
						table.append((section.name, inv_name_short, game.localize(description) if prev_description != description else '↑'))
						prev_description = description
				print_table(table)
				return sections

			def print_actor_outfit_html():
				sections = get_table(game.outfits_iter)  # collect all outfits and its .ltx sections
				graphs = (
					GraphParams('hit_fraction_actor', '(less is stronger)'),
					GraphParams('strike_protection', '(more is stronger)'),
					GraphParams('radiation_protection', '(more is stronger)'),
					GraphParams('explosion_protection', '(more is stronger)'),
					GraphParams('fire_wound_protection', '(more is stronger)'),
					GraphParams('wound_protection', '(more is stronger)'),
					GraphParams('shock_protection', '(more is stronger)'),
					GraphParams('burn_protection', '(more is stronger)'),
					GraphParams('chemical_burn_protection', '(more is stronger)'),
					GraphParams('telepatic_protection', '(more is stronger)'),
					)
				print_graphs(sections, graphs)

			def print_damages_html(value_name='hit_fraction', title='NPC stalkers vulnerability', xlabel='(less is stronger)'):
				# collect all damages and its .ltx sections
				sections = sorted((section for section in game.damages_iter()), key=lambda section: section.name)
				graphs = (
					GraphParams('hit_fraction', '(less is stronger)'),
					)
				print_graphs(sections, graphs, 1)

			def print_amunition_html():
				sections = get_table(game.ammo_iter)  # collect all ammo and its .ltx sections
				graphs = (
					GraphParams('k_hit', '(more is stronger)'),
					GraphParams('k_impulse', '(more is stronger)'),
					GraphParams('k_pierce', '(more is stronger)', True),
					GraphParams('k_ap', '(more is stronger)', True),
					GraphParams('k_dist', '(more is longer range)'),
					GraphParams('k_disp', '(more is less accurately)'),
					GraphParams('k_air_resistance', '(more is more resistance)'),
					)
				print_graphs(sections, graphs, 1)

			def print_weapons_html(ef_weapon_type: str):

				def pistol_iter():
					for section in game.weapons_iter():
						if section.name == 'wpn_pb':
							pass
						if ef_weapon_type == section.get('ef_weapon_type'):
							yield section

				sections = get_table(pistol_iter)
				graphs = (
					GraphParams('hit_power', '(more is stronger)'),
					GraphParams('hit_impulse', '(more is stronger)', True),
					GraphParams('bullet_speed', 'm/s', True),
					GraphParams('fire_distance', 'max, m', True),
					GraphParams('hit_probability_gd_novice', '(more is more accurate)'),
					GraphParams('fire_dispersion_base', '(less is more accurate)'),
					GraphParams('fire_dispersion_condition_factor', '(less is more accurate)'),
					GraphParams('condition_shot_dec', '(less is more reliable)', True),
					GraphParams('misfire_condition_k', '(less is more reliable)'),
					GraphParams('misfire_probability', '(less is more reliable)', True),
					)
				print_graphs(sections, graphs, 1, 1.1)

			def print_food_html():
				sections = get_table(game.food_iter)  # collect all food and its .ltx sections
				graphs = (
					GraphParams('eat_health', ''),
					GraphParams('eat_satiety', ''),
					GraphParams('eat_power', ''),
					GraphParams('eat_radiation', ''),
					GraphParams('eat_alcohol', ''),
					GraphParams('satiety_slake_factor', ''),
					)
				print_graphs(sections, graphs)

			def print_medkit_html():
				SGM_EXCLUDE_PREFIXES = ('medal_', 'dv_', 'outfit_upgrade_', 'repair_', 'skill_', 'personal_rukzak', 'sleeping_bag')
				sections = get_table(game.medkit_iter, SGM_EXCLUDE_PREFIXES)  # collect all medkit and its .ltx sections
				graphs = (
					GraphParams('eat_health', ''),
					GraphParams('eat_satiety', ''),
					GraphParams('eat_power', ''),
					GraphParams('eat_radiation', ''),
					GraphParams('eat_alcohol', ''),
					GraphParams('satiety_slake_factor', ''),
					)
				print_graphs(sections, graphs)

			def print_artefact_html():
				sections = get_table(game.artefact_iter)  # collect all artefact and its .ltx sections
				graphs = (
					GraphParams('af_rank', ''),
					GraphParams('health_restore_speed', ''),
					GraphParams('radiation_restore_speed', ''),
					GraphParams('satiety_restore_speed', ''),
					GraphParams('power_restore_speed', ''),
					GraphParams('bleeding_restore_speed', ''),
					GraphParams('additional_inventory_weight', ''),
					GraphParams('additional_inventory_weight2', ''),
					)
				print_graphs(sections, graphs, 1, 1.15)

			print(f'<h1>{args.head}<h1><hr/>')

			game = Game(gamedata_path, args.localization)
			pio.templates.default = 'plotly_dark'

			print('<h2>1 Actor outfits</h2>')

			print_actor_outfit_html()

			print('<h2>2 NPC armor</h2>')
			print_damages_html()

			print('<h2>3 Ammunition tactical parameters</h2>')
			print_amunition_html()

			print('<h2>4 Weapon tactical parameters</h2>')
			for index, (ef_weapon_type, text) in enumerate((('5', 'Pistols'), ('6', 'Assault rifles'), ('7', 'Rifles'), ('8', 'Guns'))):
				print(f'<h3>4.{index + 1} {text}</h3>')
				print_weapons_html(ef_weapon_type)

			print('<h2>5 Food tactical parameters</h2>')
			print_food_html()

			print('<h2>6 Medkit tactical parameters</h2>')
			print_medkit_html()

			print('<h2>7 Artefact tactical parameters</h2>')
			print_artefact_html()

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
