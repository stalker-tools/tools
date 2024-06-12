#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Iterator
from typing import NamedTuple
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
# stalker-tools import
from ltx_tool import Ltx
from game import Game
from icon_tools import IconsEquipment, get_image_as_html_img


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():


		class GraphParams(NamedTuple):
			value_name: str
			value_label: str
			log_axies: bool = False
			title: str | None = None
			format: str | None = None

			def get_title(self):
				return self.title if self.title else self.value_name

			def get_value(self, section: Ltx.Section) -> float:
				match self.format:
					case None:
						return get_float_value(section.get(self.value_name))
					case '%':
						return int(get_float_value(section.get(self.value_name)) * 10000) / 100
					case '1-%':
						return 100 - int(get_float_value(section.get(self.value_name)) * 10000) / 100

			def get_str(self, section: Ltx.Section) -> str:
				value = self.get_value(section)
				if value < 1:
					return f'{value:.2f}'
				elif value < 10:
					return f'{value:.1f}'
				return f'{value:.0f}'


		class GraphParamsCondition(GraphParams):
			def get_value(self, section: Ltx.Section) -> float:
				condition_shot_dec = get_float_value(section.get('condition_shot_dec'))
				misfire_condition_k = get_float_value(section.get('misfire_condition_k'))
				shots_count = (1 - misfire_condition_k) / condition_shot_dec
				return shots_count


		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray .ltx file parser. Out format: plotly graphs embedded in html as images',
				epilog=f'Examples: {argv[0]} -tb -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky" > "ClearSky_brochure.htm"',
			)
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('--head', default='S.T.A.L.K.E.R.', metavar='TEXT', help='head text')
			parser.add_argument('-s', '--style', metavar='STYLE', default='dark', help='style: l - light, d - dark (default)')
			parser.add_argument('-t', '--type', metavar='TYPE', default='a', help='type: a - analyse (default), b - brochure')
			return parser.parse_args()

		args = parse_args()

		def get_table(game, iter_sections: Iterator[Ltx.Section], exclude_prefixes: list[str] = None, localized_only = False) -> list[tuple[Ltx.Section, str]]:
			'''
			return sorted and filtered sections with localized inv_name_short
			exclude_prefixes - filter by section name (name prefix or entire name)'''

			def iter_sections_for_sorting() -> Iterator[tuple[Ltx.Section, str]]:
				for section in iter_sections():
					if (sorted_text := game.localize(section.get('inv_name_short')) if localized_only else section.name):
						yield section, sorted_text.replace(',', '.').replace('х', 'x')

			sections: list[tuple[Ltx.Section, str]] = []  # list of tuple: (section, localized inv_name_short)
			# get sorted and filtered ltx sections
			for section, _ in sorted(((section, sorted_text) for section, sorted_text in iter_sections_for_sorting()), key=lambda x: x[1]):
				if exclude_prefixes and any(section.name.startswith(x) for x in exclude_prefixes):
					continue
				if (inv_name_short := game.localize(section.get('inv_name_short'), localized_only=localized_only)):
					sections.append((section, inv_name_short))
			return sections

		def get_float_value(value: str | tuple[str]) -> float:
			if value:
				value = value[0] if type(value) is tuple else value
				value = value.replace(' ', '')
				return float(value)
			return 0

		def print_graphs(sections: list[tuple[Ltx.Section, str]], graphs_params: list[GraphParams], group_name_index=0, width_k=None, localized=False):
			sections = sections[::-1]
			sections_names = tuple(inv_name_short_localized if localized else section.name for (section, inv_name_short_localized) in sections)
			fig = make_subplots(rows=1, cols=len(graphs_params), subplot_titles=tuple(x.get_title() for x in graphs_params), horizontal_spacing=.08/len(graphs_params))
			bar_width, bgcolor = .45, 'rgba(50,50,50,28)'

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
				values = tuple(graphs_param.get_value(section) for (section, _) in sections)
				fig.append_trace(
					go.Bar(x=values, y=sections_names, orientation='h', width=bar_width, marker={'color': colors}),
					row=1, col=index + 1)
				fig.update_xaxes(title=graphs_param.value_label, col=index + 1)
				if graphs_param.log_axies:
					fig.update_xaxes(type='log')
			
			fig.update_layout(autosize=False, height=50 + len(sections) * 25, width=(175 + 160 * len(graphs_params)) * (width_k if width_k else 1),
				bargap=.01, bargroupgap=.01,
				margin={'l': 5, 'r': 5, 't': 30, 'b': 5}, showlegend=False, barmode='group')
			match args.style:
				case 'd' | 'dark':
					fig.update_layout(paper_bgcolor=bgcolor, plot_bgcolor=bgcolor)
			fig.update_xaxes(showgrid=True, showline=True, linewidth=2, griddash='dash', gridcolor='black')
			for trace_index in range(2, len(fig.data) + 1):
				fig.update_yaxes(visible=False, col=trace_index)

			print(fig.to_image('svg').decode())

		def analyse(gamedata_path: str):

			def get_value(text: str, type_=float) -> 'type_ | None':
				try:
					return type_(text)
				except:
					return None

			def remove_prefix(name: str, prefix: str) -> str:
				return name[len(prefix):] if name.startswith(prefix) else name

			def print_table(sections: list[tuple[Ltx.Section, str]]):
				FILELD_NAMES = ('No', 'Section name', 'Name', 'Icon', 'Description')
				STYLE = 'style="text-align: left;"'
				print(f'<table border=1 style="border-collapse:collapse">')
				print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead><tbody>')
				prev_description = None
				for index, (section, _) in enumerate(sections):
					inv_name_short, description = game.localize(section.get('inv_name_short')), section.get("description")
					if index == 0:
						print('<tr style="border-left-style:hidden;border-right-style:hidden">')
					else:
						print('<tr style="border-style:hidden">')
					print(f'<th>{index + 1}</th>')
					print(f'<th {STYLE}><span style="text-decoration: underline dotted;">{game.paths.relative(section.ltx.ltx_file_path)}</span><br/>{section.name}</th>')
					print(f'<th>{inv_name_short}</th>')
					inv_grid = (int(section.get('inv_grid_x')), int(section.get('inv_grid_y')), int(section.get('inv_grid_width', 1)), int(section.get('inv_grid_height', 1)))
					print(f'<th>{get_image_as_html_img(icons.get_image(*inv_grid))}</th>')
					print(f'<th {STYLE}>{game.localize(description, True) if prev_description != description else "↑"}</th>')
					print('</tr>')
					prev_description = description
				print(f'</tbody></table><p/>')

			def print_actor_outfit_html():
				sections = get_table(game, game.outfits_iter)  # collect all outfits and its .ltx sections
				print_table(sections)
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
				print_graphs(sections, graphs, width_k=1.05)

			def print_damages_html(value_name='hit_fraction', title='NPC stalkers vulnerability', xlabel='(less is stronger)'):
				# collect all damages and its .ltx sections
				sections = sorted(((section, '') for section in game.damages_iter()), key=lambda x: x[0].name)
				graphs = (
					GraphParams('hit_fraction', '(less is stronger)'),
					)
				print_graphs(sections, graphs, 1)

			def print_amunition_html():
				sections = get_table(game, game.ammo_iter)  # collect all ammo and its .ltx sections
				print_table(sections)
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

				sections = get_table(game, pistol_iter)
				print_table(sections)
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
				sections = get_table(game, game.food_iter)  # collect all food and its .ltx sections
				print_table(sections)
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
				sections = get_table(game, game.medkit_iter, SGM_EXCLUDE_PREFIXES)  # collect all medkit and its .ltx sections
				print_table(sections)
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
				sections = get_table(game, game.artefact_iter)  # collect all artefact and its .ltx sections
				print_table(sections)
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

			print(f'<html><head><title>{args.head}</title></head>')
			print(f'<body>')
			print(f'<h1>{args.head}<h1><hr/>')

			game = Game(gamedata_path, args.localization)
			icons = IconsEquipment(gamedata_path)
			match args.style:
				case 'd' | 'dark':
					pio.templates.default = 'plotly_dark'

			print('<h2>Content</h2>')
			print('<p><a href="#1">1 Actor outfits</a></p>')
			print('<p><a href="#2">2 NPC armor</a></p>')
			print('<p><a href="#3">3 Ammunition tactical parameters</a></p>')
			print('<p><a href="#4.1">4.1 Weapon tactical parameters: Pistols</a></p>')
			print('<p><a href="#4.2">4.2 Weapon tactical parameters: Assault rifles</a></p>')
			print('<p><a href="#4.3">4.3 Weapon tactical parameters: Rifles</a></p>')
			print('<p><a href="#4.4">4.4 Weapon tactical parameters: Guns</a></p>')
			print('<p><a href="#5">5 Food tactical parameters</a></p>')
			print('<p><a href="#6">6 Medkit tactical parameters</a></p>')
			print('<p><a href="#7">7 Artefact tactical parameters</a></p>')

			print('<h2 id="1">1 Actor outfits</h2>')
			print_actor_outfit_html()

			print('<h2 id="2">2 NPC armor</h2>')
			print_damages_html()

			print('<h2 id="3">3 Ammunition tactical parameters</h2>')
			print_amunition_html()

			print('<h2 id="4">4 Weapon tactical parameters</h2>')
			for index, (ef_weapon_type, text) in enumerate((('5', 'Pistols'), ('6', 'Assault rifles'), ('7', 'Rifles'), ('8', 'Guns'))):
				print(f'<h3 id="4.{index + 1}">4.{index + 1} {text}</h3>')
				print_weapons_html(ef_weapon_type)

			print('<h2 id="5">5 Food tactical parameters</h2>')
			print_food_html()

			print('<h2 id="6">6 Medkit tactical parameters</h2>')
			print_medkit_html()

			print('<h2 id="7">7 Artefact tactical parameters</h2>')
			print_artefact_html()

			print(f'</body></html>')

		def brochure(gamedata_path: str):

			def print_html(sections: list[tuple[Ltx.Section, str]], graphs: list[GraphParams], chapter: str | None = None, k_width = 1):

				def get_parameters(graphs, section):
					return "<br/>".join(f'{graph.get_title()}: {graph.get_str(section)}' for graph in graphs if section.get(graph.value_name) is not None)

				print(f'<div class="main">')
				for index, (section, inv_name_short_localized) in enumerate(sections):
					inv_grid = (int(section.get('inv_grid_x')), int(section.get('inv_grid_y')), int(section.get('inv_grid_width', 1)), int(section.get('inv_grid_height', 1)))
					print(f'<div class="item"><div style="display:flex;align-items:flex-start;">{index+1} {get_image_as_html_img(icons.get_image(*inv_grid))}<br/><span class="item-header">{inv_name_short_localized}</span></div><div style="display:flex;align-items:end;">{get_parameters(graphs, section)}</div></div>')
					# <div>{game.localize(section.get("description"))}</div>
				print('</div>')

				if chapter:
					print(f'<h3>{chapter}: сводная таблица</h3>')
				print_graphs(sections, graphs, width_k=1.05, localized=True)

				if chapter:
					print(f'<h3>{chapter}: описание</h3>')
				prev_description = None
				print(f'<div class="description">')
				for index, (section, inv_name_short_localized) in enumerate(sections):
					inv_grid = (int(section.get('inv_grid_x')), int(section.get('inv_grid_y')), int(section.get('inv_grid_width', 1)), int(section.get('inv_grid_height', 1)))
					description = game.localize(section.get('description'), True)
					if prev_description == description:
						description = '&nbsp;↑'
					else:
						prev_description = description
					img = icons.get_image(*inv_grid)
					img = img.resize((int(img.width * 1.5), int(img.height * 1.5)))
					print(f'<div class="item-description stroke-bg">{index+1}{get_image_as_html_img(img)}<span class="item-header">{inv_name_short_localized}</span><br/>')
					if (ammo_class := section.get('ammo_class')):  # has ammo
						if type(ammo_class) is str:
							ammo_class = (ammo_class,)
						buff = set()
						for ac in ammo_class:
							for ammo_section in game.ammo_iter():
								if ammo_section.name == ac:
									buff.add(game.localize(ammo_section.get('inv_name_short')).replace(',', '.'))
						print(f'• Боеприпасы: {", ".join(buff)}<br/>')
					print(f'{description}')
					print('</div>')
				print('</div>')

			def print_actor_outfit_html(chapter: str):
				graphs = (
					GraphParams('hit_fraction_actor', 'меньше - лучше', title='Пулезащита', format='1-%'),
					GraphParams('strike_protection', 'больше - лучше', title='Ударопрочность', format='%'),
					GraphParams('radiation_protection', 'больше - лучше', title='Радиозащита', format='%'),
					GraphParams('explosion_protection', 'больше - лучше', title='Взрывозащита', format='%'),
					GraphParams('fire_wound_protection', 'больше - лучше', title='Индикация', format='%'),
					GraphParams('wound_protection', 'больше - лучше', title='Ранения', format='%'),
					GraphParams('shock_protection', 'больше - лучше', title='Электрозащита', format='%'),
					GraphParams('burn_protection', 'больше - лучше', title='Огнезащита', format='%'),
					GraphParams('chemical_burn_protection', 'больше - лучше', title='Химзащита', format='%'),
					GraphParams('telepatic_protection', 'больше - лучше', title='Телепатия', format='%'),
					GraphParams('cost', '', title='Цена'),
					)
				sections = get_table(game, game.outfits_iter, localized_only=True)  # collect all outfits and its .ltx sections
				print_html(sections, graphs, chapter)

			def print_amunition_html(chapter: str):
				graphs = (
					GraphParams('k_hit', 'больше - мощнее', title='Мощность, 300 J'),
					GraphParams('k_impulse', 'больше - мощнее', title='Импульс'),
					GraphParams('k_pierce', 'больше - мощнее', True, title='Броневоздействие'),
					GraphParams('k_ap', 'больше - мощнее', True, title='Бронебойность'),
					GraphParams('k_dist', 'больше - дальше', title='Дистанция'),
					GraphParams('k_disp', 'больше - менее точно', title='Дисперсия'),
					GraphParams('k_air_resistance', 'больше - выше сопротивление', title='Сопротивление'),
					GraphParams('cost', '', title='Цена'),
					)
				sections = get_table(game, game.ammo_iter, localized_only=True)  # collect all ammo and its .ltx sections
				print_html(sections, graphs, chapter)

			def print_weapons_html(ef_weapon_type: str, chapter: str, k_width = 1):

				def pistol_iter():
					for section in game.weapons_iter():
						if section.name == 'wpn_pb':
							pass
						if ef_weapon_type == section.get('ef_weapon_type'):
							yield section

				sections = get_table(game, pistol_iter, localized_only=True)
				graphs = (
					GraphParams('hit_power', 'больше - мощнее', title='Коэф. мощности патрона, %', format='%'),
					GraphParams('silencer_hit_power', 'больше - мощнее', title='&nbsp;&nbsp;&nbsp;тоже с глушителем, %', format='%'),
					GraphParams('hit_impulse', 'больше - мощнее', True, title='Импульс'),
					GraphParams('bullet_speed', 'м/с', True, title='Скорость пули, м/с'),
					GraphParams('fire_distance', 'макс, м', True, title='Дистанция, м'),
					GraphParams('hit_probability_gd_novice', 'больше - точнее', title='Вероятн. попадания, %', format='%'),
					GraphParams('fire_dispersion_base', 'меньше - точнее', title='Дисперсия, база'),
					GraphParams('fire_dispersion_condition_factor', 'меньше - точнее', title='Дисперсия, макс.'),
					# GraphParams('condition_shot_dec', 'меньше - надёжнее', True, title='Уменьш. при выстреле', format='%'),
					# GraphParams('misfire_condition_k', 'меньше - надёжнее', title='Состояние: осечки', format='%'),
					GraphParamsCondition('condition_shot_dec', 'больше - надёжнее', title='Ресурс, выстрелов'),
					GraphParams('misfire_probability', 'меньше - надёжнее', True, title='Вероятн. осечки, %', format='%'),
					GraphParams('cost', '', title='Цена'),
					)
				print_html(sections, graphs, chapter, k_width)

			def print_food_html(chapter: str):
				sections = get_table(game, game.food_iter, localized_only=True)  # collect all food and its .ltx sections
				graphs = (
					GraphParams('eat_health', '', title='Восстановление здоровья, %', format='%'),
					GraphParams('eat_satiety', '', title='Повышение сытости, %', format='%'),
					GraphParams('eat_power', '', title='Восстановление сил, %', format='%'),
					GraphParams('eat_radiation', '', title='Радиация, %', format='%'),
					GraphParams('eat_alcohol', '', title='Алкоголь, %', format='%'),
					GraphParams('satiety_slake_factor', '', title='Насыщение, %'),
					GraphParams('cost', '', title='Цена'),
					)
				print_html(sections, graphs, chapter)

			def print_medkit_html(chapter: str):
				SGM_EXCLUDE_PREFIXES = ('medal_', 'dv_', 'outfit_upgrade_', 'repair_', 'skill_', 'personal_rukzak', 'sleeping_bag')
				sections = get_table(game, game.medkit_iter, SGM_EXCLUDE_PREFIXES, localized_only=True)  # collect all medkit and its .ltx sections
				graphs = (
					GraphParams('eat_health', '', title='Восстановление здоровья, %', format='%'),
					GraphParams('eat_satiety', '', title='Повышение сытости, %', format='%'),
					GraphParams('eat_power', '', title='Восстановление сил, %', format='%'),
					GraphParams('eat_radiation', '', title='Радиация, %', format='%'),
					GraphParams('eat_alcohol', '', title='Алкоголь, %', format='%'),
					GraphParams('satiety_slake_factor', '', title='Насыщеие, %'),
					GraphParams('cost', '', title='Цена'),
					)
				print_html(sections, graphs, chapter)

			def print_artefact_html(chapter: str):
				sections = get_table(game, game.artefact_iter, localized_only=True)  # collect all artefact and its .ltx sections
				graphs = (
					GraphParams('af_rank', '', title='Ранг'),
					GraphParams('health_restore_speed', '', title='Восстановление здоровья'),
					GraphParams('radiation_restore_speed', '', title='Радиация'),
					GraphParams('satiety_restore_speed', '', title='Сытость'),
					GraphParams('power_restore_speed', '', title='Выносливость'),
					GraphParams('bleeding_restore_speed', '', title='Кровотечение'),
					GraphParams('additional_inventory_weight', '', title='Вес'),
					GraphParams('additional_inventory_weight2', '', title='Вес 2'),
					GraphParams('cost', '', title='Цена'),
					)
				print_html(sections, graphs, chapter)

			k_width = 1

			print(f'<html><head><title>{args.head}</title></head>')
			print(f'''<style>
.main {{ display:grid;grid-template-columns:repeat(auto-fill,{int(375*k_width)}px); }}
.description {{ display:grid;grid-template-columns:repeat(auto-fill,{670*k_width}px);grid-template-rows:min-content;align-content:flex-start; }}
.item {{ display:grid;padding:10px;margin:7px;border:1px outset;border-radius:15px;align-items:flex-start;grid-template-rows:min-content; }}
.item-description {{ display:grid;padding:10px;margin:7px; }}
.item-header {{ font-weight:bold;font-size:larger; }}
.stroke-bg {{
background: url("data:image/svg+xml,%3Csvg viewBox='0 0 20 300' xmlns='http://www.w3.org/2000/svg'%3E %3Cpath vector-effect='non-scaling-stroke' transform='rotate(-30)' opacity='15%' stroke='currentColor' d='M 0,0 l 0,100'/%3E %3Cpath stroke='currentColor' d='M 0,0 l 20,0'/%3E %3C/svg%3E");
}}
</style>''')
			print(f'</head>')
			print(f'<body>')
			print(f'<h1>{args.head}<h1><hr/>')

			game = Game(gamedata_path, args.localization, False)
			icons = IconsEquipment(gamedata_path)
			match args.style:
				case 'd' | 'dark':
					pio.templates.default = 'plotly_dark'

			print('<h2>Содержание</h2>')
			print('<p><a href="#1">1 Защитные костюмы</a></p>')
			print('<p><a href="#2">2 Патроны</a></p>')
			print('<p><a href="#3.1">3.1 Оружие: Пистолеты</a></p>')
			print('<p><a href="#3.2">3.2 Оружие: Автоматы</a></p>')
			print('<p><a href="#3.3">3.3 Оружие: Ружья</a></p>')
			print('<p><a href="#3.4">3.4 Оружие: Винтовки/пулемёты</a></p>')
			print('<p><a href="#4">4 Продовольствие</a></p>')
			print('<p><a href="#5">5 Медицинские препараты</a></p>')
			print('<p><a href="#6">6 Артефакты</a></p>')

			print(f'<hr/>')
			print('<h2 id="1">1 Защитные костюмы</h2>')
			print_actor_outfit_html('Защитные костюмы')

			print(f'<hr/>')
			print('<h2 id="2">2 Патроны</h2>')
			print_amunition_html('Патроны')

			print(f'<hr/>')
			print('<h2 id="3">3 Оружие</h2>')
			for index, (ef_weapon_type, text) in enumerate((('5', 'Пистолеты'), ('6', 'Автоматы'), ('7', 'Ружья'), ('8', 'Винтовки/пулемёты'))):
				print(f'<h3 id="3.{index + 1}">3.{index + 1} {text}</h3>')
				print_weapons_html(ef_weapon_type, text, 1 if index == 0 else 1.4)

			print(f'<hr/>')
			print('<h2 id="4">4 Продовольствие</h2>')
			print_food_html('Продовольствие')

			print(f'<hr/>')
			print('<h2 id="5">5 Медицинские препараты</h2>')
			print_medkit_html('Медицинские препараты')

			print(f'<hr/>')
			print('<h2 id="6">6 Артефакты</h2>')
			print_artefact_html('Артефакты')

			print(f'</body></html>')

		match args.type:
			case 'b':
				brochure(args.gamedata)
			case _:
				analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
