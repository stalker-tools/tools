#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Stalker tools, 2023-2026

from collections.abc import Iterator, Callable
from typing import NamedTuple, Literal, Self
from datetime import datetime
from configparser import ConfigParser
from pathlib import Path
from sys import stdout
from os.path import sep as os_sep
import difflib
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
from PIL.Image import open as image_open, Image
from PIL import ImageDraw
# stalker-tools import
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from ltx_tool import Ltx, update_section_values, has_include
from paths import Paths, Config as PathsConfig, DbFileVersion, DEFAULT_GAMEDATA_PATH
from GameConfig import GameConfig
from icon_tools import IconsEquipment, get_image_as_html_img


class BrochureConfig(NamedTuple):
	caption: str
	author: str
	head: str
	head_pictures: tuple[str]
	head_intro: str
	style: Literal['d', 'dark']
	localization: str
	path: Path

	@classmethod
	def from_file(cls, path: str) -> Self:
		config_parser = ConfigParser()
		config_parser.read(path)
		caption = config_parser.get('global', 'caption', fallback=None)
		author = config_parser.get('global', 'author', fallback=None)
		localization = config_parser.get('global', 'localization', fallback=None)
		style = config_parser.get('global', 'style', fallback=None)
		head = config_parser.get('head', 'title', fallback=None)
		head_pictures = config_parser.get('head', 'pictures', fallback=None)
		head_intro = config_parser.get('head', 'intro', fallback=None)
		if head_pictures:
			head_pictures = head_pictures.split(',')
		ret = cls(caption, author, head, head_pictures, head_intro, style, localization, Path(path))
		return ret


class GraphParams(NamedTuple):
	value_name: str
	value_label: str
	log_axies: bool = False
	title: str | None = None
	format: Literal['%', '1-%'] | None = None

	def get_title(self):
		return self.title if self.title else self.value_name

	def get_value(self, section: Ltx.Section) -> float:
		try:
			match self.format:
				case None:
					# pure numeric value
					return self.get_float_value(section.get(self.value_name))
				case '%':
					# percent value: 1% = 0.01, 100% = 1.0
					return int(self.get_float_value(section.get(self.value_name)) * 10000) / 100
				case '1-%':
					# percent inverted value: 1% = 0.99, 100% = 0.0
					return 100 - int(self.get_float_value(section.get(self.value_name)) * 10000) / 100
		except ValueError as ex:
			ex.add_note(f'Section: {section.name}; Ltx file: "{section.ltx.ltx_file_path}"')
			raise ex

	def get_str(self, section: Ltx.Section) -> str:
		value = self.get_value(section)
		if value < 1:
			return f'{value:.2f}'
		elif value < 10:
			return f'{value:.1f}'
		return f'{value:.0f}'

	@staticmethod
	def get_float_value(value: str | tuple[str], first_item = False) -> float:
		if value:
			value = value[0 if first_item else -1] if type(value) is tuple else value
			value = value.replace(' ', '')
			return float(value)
		return 0


class GraphParamsCondition(GraphParams):
	def get_value(self, section: Ltx.Section) -> float:
		condition_shot_dec = self.get_float_value(section.get('condition_shot_dec'))
		misfire_condition_k = self.get_float_value(section.get('misfire_condition_k'))
		shots_count = (1 - misfire_condition_k) / condition_shot_dec
		return shots_count


def path_to_os(path: str | Path) -> str:
	'converts path separator according to os'
	if isinstance(path, Path):
		path = str(path)
	return path.replace('/' if os_sep == '\\' else '\\', os_sep)

def get_inv_grid(ltx_section: Ltx.Section | None) -> tuple[int, int, int, int] | None:
	'returns .ltx section inventory grid square: coordinate and size (inv_grid_*)'
	if not ltx_section:
		return None
	try:
		return (int(ltx_section.get('inv_grid_x')), int(ltx_section.get('inv_grid_y')), int(ltx_section.get('inv_grid_width', 1)), int(ltx_section.get('inv_grid_height', 1)))
	except TypeError:
		return None

def get_image_by_inv_grid(icons: IconsEquipment, ltx_section: Ltx.Section) -> Image | None:
	'returns image from .dds according to .ltx section inventory grid square (inv_grid_*)'
	if icons and ltx_section:
		if (inv_grid := get_inv_grid(ltx_section)):
			return icons.get_image(*inv_grid)
	return None

def get_texture_from_ogf(paths: Paths, ogf_file_path: str) -> str | None:
	'returns texture file path; tries to extract texture .dds file path ftom content of .ogf file'
	try:
		with paths.open(str(Path('meshes') / ogf_file_path), 'rb') as f:
			if (buff := f.read(1024)):
				if (texture_end_index := buff.find(b'\x00models\\')) > 0 and (texture_start_index := buff.rfind(b'\x00', 0, texture_end_index-1)):
					return buff[texture_start_index+1:texture_end_index].decode()
	except FileNotFoundError: pass
	return None

def get_table(game, iter_sections: Iterator[Ltx.Section], exclude_prefixes: list[str] = None, localized_only = False) -> list[tuple[Ltx.Section, str, str]]:
	'''
	return sorted and filtered sections with localized inv_name_short and localized inv_name
	exclude_prefixes - filter by section name (name prefix or entire name)'''

	def iter_sections_for_sorting() -> Iterator[tuple[Ltx.Section, str]]:
		for section in iter_sections():
			if (sorted_text := game.localize(section.get('inv_name_short') or section.get('inv_name')) if localized_only else section.name):
				yield section, sorted_text.replace(',', '.').replace('х', 'x')

	sections: list[tuple[Ltx.Section, str, str]] = []  # list of tuple: (section, localized inv_name_short, localized inv_name)
	# get sorted and filtered ltx sections
	for section, _ in sorted(((section, sorted_text) for section, sorted_text in iter_sections_for_sorting()), key=lambda x: x[1]):
		if exclude_prefixes and any(section.name.startswith(x) for x in exclude_prefixes):
			continue
		if (inv_name_short := game.localize(section.get('inv_name_short') or section.get('inv_name'), localized_only=localized_only)):
			inv_name = game.localize(section.get('inv_name'), localized_only=localized_only)
			sections.append((section, inv_name_short, inv_name))
	return sections

def print_graphs(sections: list[tuple[Ltx.Section, str, str]], graphs_params: list[GraphParams], group_name_index=0, width_k=None, localized=False, style: None | Literal['d', 'dark'] = None):
	sections = sections[::-1]
	sections_names = tuple(inv_name_short_localized if localized else section.name for (section, inv_name_short_localized, _) in sections)
	fig = make_subplots(rows=1, cols=len(graphs_params), subplot_titles=tuple(x.get_title() for x in graphs_params), horizontal_spacing=.08/len(graphs_params))
	bar_width, bgcolor = .45, 'rgba(50,50,50,28)'

	def get_colors(names: tuple[str]) -> tuple[str]:
		cycle_colors = pio.templates[pio.templates.default].layout.colorway
		if not cycle_colors:
			cycle_colors = (0x1f77b4, 0xff7f0e, 0x2ca02c, 0xd62728, 0x9467bd, 0x8c564b, 0xe377c2, 0x7f7f7f, 0xbcbd22, 0x17becf)
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
		values = tuple(graphs_param.get_value(section) for (section, _, _) in sections)
		fig.append_trace(
			go.Bar(x=values, y=sections_names, orientation='h', width=bar_width, marker={'color': colors}),
			row=1, col=index + 1)
		fig.update_xaxes(title=graphs_param.value_label, col=index + 1)
		if graphs_param.log_axies:
			fig.update_xaxes(type='log')
	
	fig.update_layout(autosize=False, height=50 + len(sections) * 25, width=(175 + 160 * len(graphs_params)) * (width_k if width_k else 1),
		bargap=.01, bargroupgap=.01,
		margin={'l': 5, 'r': 5, 't': 30, 'b': 5}, showlegend=False, barmode='group')
	match style:
		case 'd' | 'dark':
			fig.update_layout(paper_bgcolor=bgcolor, plot_bgcolor=bgcolor)
	fig.update_xaxes(showgrid=True, showline=True, linewidth=2, griddash='dash', gridcolor='black')
	for trace_index in range(2, len(fig.data) + 1):
		fig.update_yaxes(visible=False, col=trace_index)

	print(fig.to_image('svg').decode())

def analyse(gamedata: PathsConfig | str, config: BrochureConfig, verbose = 0):

	def get_value(text: str, type_=float) -> 'type_ | None':
		try:
			return type_(text)
		except:
			return None

	def remove_prefix(name: str, prefix: str) -> str:
		return name[len(prefix):] if name.startswith(prefix) else name

	def print_table(sections: list[tuple[Ltx.Section, str, str]]):

		def visual() -> str:
			'returns visual .ogf file path and try extract texture .dds file path ftom content of .ogf file'
			if (visual := section.get('visual')):
				if not visual.endswith('.ogf'):
					visual += '.ogf'
				if (texture := get_texture_from_ogf(game.paths, visual)):
					return rf' visual={visual} texture={texture}'  # do not use {visual=} - r-string not working
				return rf' visual={visual}'
			return ''

		def hud() -> str:
			if (hud := section.get('hud')):
				return f' {hud=}'
			return ''

		FILELD_NAMES = ('No', 'Section File/Name', 'inv_name_short', 'inv_name', 'Icon', 'description')
		STYLE = 'style="text-align: left;"'
		print(f'<table border=1 style="border-collapse:collapse">')
		print(f'<thead><tr>{"".join(("<th>"+x+"</th>" for x in FILELD_NAMES))}</tr></thead><tbody>')
		prev_description = None
		for index, (section, _, _) in enumerate(sections):
			# row with base info
			inv_name_short, inv_name, description = game.localize(section.get('inv_name_short')), game.localize(section.get('inv_name')), section.get("description")
			if index == 0:
				print('<tr style="border-left-style:hidden;border-right-style:hidden">')
			else:
				print('<tr style="border-style:hidden">')
			print(f'<th>{index + 1}</th>')
			print(f'<th {STYLE}><span style="text-decoration: underline dotted;">{game.paths.relative(section.ltx.ltx_file_path)}</span><br/>[{section.name}]</th>')
			print(f'<th>{inv_name_short}</th>')
			print(f'<th>{inv_name}</th>')
			print(f'<th>{get_image_as_html_img(get_image_by_inv_grid(icons, section))}</th>')
			print(f'<th {STYLE}>{game.localize(description, True) if prev_description != description else "↑"}</th>')
			print('</tr>')
			# row with info for developers
			print('<tr>')
			print(f'<th align="left" style="border-style:hidden" colspan="{len(FILELD_NAMES)}">inv=({section.get("inv_grid_x")},{section.get("inv_grid_y")} {section.get("inv_grid_width")}x{section.get("inv_grid_height")}){visual()}{hud()}</th>')
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
		print_graphs(sections, graphs, width_k=1.05, style=config.style)

	def print_damages_html(value_name='hit_fraction', title='NPC stalkers vulnerability', xlabel='(less is stronger)'):
		# collect all damages and its .ltx sections
		sections = sorted(((section, '', '') for section in game.damages_iter()), key=lambda x: x[0].name)
		graphs = (
			GraphParams('hit_fraction', '(less is stronger)'),
			)
		print_graphs(sections, graphs, 1, style=config.style)

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
			GraphParams('cost', 'rub'),
			)
		print_graphs(sections, graphs, 1, style=config.style)

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
			GraphParams('cost', 'rub'),
			)
		print_graphs(sections, graphs, 1, 1.1, style=config.style)

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
			GraphParams('cost', 'rub'),
			)
		print_graphs(sections, graphs, style=config.style)

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
			GraphParams('cost', 'rub'),
			)
		print_graphs(sections, graphs, style=config.style)

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
			GraphParams('cost', ''),
			)
		print_graphs(sections, graphs, 1, 1.15, style=config.style)

	print(f'<html><head><title>{config.caption}</title></head>')
	print(f'<body>')
	print(f'<h1>{config.head}<h1><hr/>')

	if verbose:
		print('<h2>Log:</h2><pre>')
	game = gamedata
	game = GameConfig(gamedata, config.localization, verbose)
	icons = IconsEquipment(game.paths)
	if verbose:
		print('</pre>')

	match config.style:
		case 'd' | 'dark':
			pio.templates.default = 'plotly_dark'
		case _:
			pio.templates.default = config.style

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

def brochure(gamedata: PathsConfig | str, config: BrochureConfig):

	def print_html(sections: list[tuple[Ltx.Section, str, str]], graphs: list[GraphParams], chapter: str | None = None, k_width = 1):

		def get_parameters(graphs, section):
			return "<br/>".join(f'{graph.get_title()}: {graph.get_str(section)}' for graph in graphs if section.get(graph.value_name) is not None)

		print(f'<div class="main">')
		for index, (section, inv_name_short_localized, _) in enumerate(sections):
			print(f'<div class="item"><div style="display:flex;align-items:flex-start;">{index+1} {get_image_as_html_img(get_image_by_inv_grid(icons, section))}<br/><span class="item-header">{inv_name_short_localized}</span></div><div style="display:flex;align-items:end;">{get_parameters(graphs, section)}</div></div>')
			# <div>{game.localize(section.get("description"))}</div>
		print('</div>')

		if chapter:
			print(f'<h3>{chapter}: сводная таблица</h3>')
		print_graphs(sections, graphs, width_k=1.05, localized=True)

		if chapter:
			print(f'<h3>{chapter}: описание</h3>')
		prev_description = None
		print(f'<div class="description">')
		for index, (section, inv_name_short_localized, inv_name_localized) in enumerate(sections):
			description = game.localize(section.get('description'), True)
			# keep multiline description as HTML
			while '\n ' in description:
				description = description.replace('\n ', '<br/>&nbsp;&nbsp;')
			while '\n' in description:
				description = description.replace('\n', '<br/>')
			if prev_description == description:
				# the same description as previous
				description = '&nbsp;↑'
			else:
				prev_description = description
			img = get_image_by_inv_grid(icons, section)
			img = img.resize((int(img.width * 1.5), int(img.height * 1.5)))
			print(f'<div class="item-description stroke-bg">{index+1}{get_image_as_html_img(img)}<span class="item-header">{inv_name_localized}</span><br/>')
			if (ammo_class := section.get('ammo_class')):  # has ammo
				# collect ammo into unique list
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
			GraphParams('fire_wound_protection', 'больше - лучше', title='Индикация защиты', format='%'),
			GraphParams('wound_protection', 'больше - лучше', title='Ранения', format='%'),
			GraphParams('shock_protection', 'больше - лучше', title='Электрозащита', format='%'),
			GraphParams('burn_protection', 'больше - лучше', title='Огнезащита', format='%'),
			GraphParams('chemical_burn_protection', 'больше - лучше', title='Химзащита', format='%'),
			GraphParams('telepatic_protection', 'больше - лучше', title='Телепатия', format='%'),
			GraphParams('inv_weight', '', title='Масса, кг'),
			GraphParams('cost', '', title='Цена'),
			)
		sections = get_table(game, game.outfits_iter, localized_only=True)  # collect all outfits and its .ltx sections
		print_html(sections, graphs, chapter)

	def print_amunition_html(chapter: str):
		graphs = (
			GraphParams('k_hit', 'больше - мощнее', title='Мощность, 300 Дж'),
			GraphParams('k_impulse', 'больше - мощнее', title='Импульс'),
			GraphParams('k_pierce', 'больше - мощнее', True, title='Броневоздействие'),
			GraphParams('k_ap', 'больше - мощнее', True, title='Бронебойность'),
			GraphParams('k_dist', 'больше - дальше', title='Дистанция'),
			GraphParams('k_disp', 'больше - менее точно', title='Дисперсия'),
			GraphParams('k_air_resistance', 'больше - выше сопротивление', title='Сопротивление'),
			GraphParams('inv_weight', '', title='Масса, кг'),
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
			GraphParams('hit_power', 'больше - мощнее', title='К мощности патрона, %', format='%'),
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
			GraphParams('ph_mass', '', title='Масса, кг'),
			GraphParams('cost', '', title='Цена'),
			)
		print_html(sections, graphs, chapter, k_width)

	def print_food_html(chapter: str):
		sections = get_table(game, game.food_iter, localized_only=True)  # collect all food and its .ltx sections
		graphs = (
			GraphParams('eat_health', '', title='Восст. здоровья, %', format='%'),
			GraphParams('eat_satiety', '', title='Повышение сытости, %', format='%'),
			GraphParams('eat_power', '', title='Восст. сил, %', format='%'),
			GraphParams('eat_radiation', '', title='Радиация, %', format='%'),
			GraphParams('eat_alcohol', '', title='Алкоголь, %', format='%'),
			GraphParams('satiety_slake_factor', '', title='Насыщение, %'),
			GraphParams('inv_weight', '', title='Масса, кг'),
			GraphParams('cost', '', title='Цена'),
			)
		print_html(sections, graphs, chapter)

	def print_medkit_html(chapter: str):
		SGM_EXCLUDE_PREFIXES = ('medal_', 'dv_', 'outfit_upgrade_', 'repair_', 'skill_', 'personal_rukzak', 'sleeping_bag')
		sections = get_table(game, game.medkit_iter, SGM_EXCLUDE_PREFIXES, localized_only=True)  # collect all medkit and its .ltx sections
		graphs = (
			GraphParams('eat_health', '', title='Восст. здоровья, %', format='%'),
			GraphParams('eat_satiety', '', title='Повышение сытости, %', format='%'),
			GraphParams('eat_power', '', title='Восст. сил, %', format='%'),
			GraphParams('eat_radiation', '', title='Радиация, %', format='%'),
			GraphParams('eat_alcohol', '', title='Алкоголь, %', format='%'),
			GraphParams('satiety_slake_factor', '', title='Насыщеие, %'),
			GraphParams('inv_weight', '', title='Масса, кг'),
			GraphParams('cost', '', title='Цена'),
			)
		print_html(sections, graphs, chapter)

	def print_artefact_html(chapter: str):
		sections = get_table(game, game.artefact_iter, localized_only=True)  # collect all artefact and its .ltx sections
		graphs = (
			GraphParams('af_rank', '', title='Ранг'),
			GraphParams('health_restore_speed', '', title='Восст. здоровья'),
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

	print(f'<html><head><title>{config.caption}</title></head>')
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
	print(f'<h1 align="center">{config.head}</h1><hr/>')
	if config.head_pictures:
		print('<p align="center">')
		for pict_path in config.head_pictures:
			print(f'{get_image_as_html_img(image_open(config.path.parent / pict_path))} ')
		print('</p><hr/>')
	print(f'<p align="left">{config.head_intro}<p><hr/>')

	game = gamedata
	game = GameConfig(gamedata, config.localization, False)
	icons = IconsEquipment(game.paths)
	match config.style:
		case 'd' | 'dark':
			pio.templates.default = 'plotly_dark'
		case _:
			pio.templates.default = config.style

	print('<h2>Содержание</h2>')
	print('<p><a href="#1">1 Защитные костюмы</a></p>')
	print('<p><a href="#2">2 Патроны</a></p>')
	print('<p><a href="#3">3 Оружие</a></p>')
	print('<p><a href="#3.1" style="margin-left: 2.5em;">3.1 Оружие: Пистолеты</a></p>')
	print('<p><a href="#3.2" style="margin-left: 2.5em;">3.2 Оружие: Автоматы</a></p>')
	print('<p><a href="#3.3" style="margin-left: 2.5em;">3.3 Оружие: Ружья</a></p>')
	print('<p><a href="#3.4" style="margin-left: 2.5em;">3.4 Оружие: Винтовки/пулемёты</a></p>')
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

	print(f'<hr/><p align="center">{config.author}</p>')

	print(f'</body></html>')

def get_kinds(game: GameConfig | None = None) -> dict[str, Iterator[Ltx.Section] | None]:
	'returns list of .ltx section kind filters; None is group delimiter'

	def weapons_iter() -> Iterator[Ltx.Section | None]:
		'grouped by ef_weapon_type: pistols, riffles e.t.c.'
		prev_ef_weapon_type = None
		for section in sorted(game.weapons_iter(), key=lambda x: f'{x.get("ef_weapon_type", "0")}{x.name}'):
			if prev_ef_weapon_type is None or section.get('ef_weapon_type') != prev_ef_weapon_type:
				prev_ef_weapon_type = section.get('ef_weapon_type')
				yield None
			yield section

	return {
		'ammo': game.ammo_iter if game else None,
		'weapons': game.weapons_iter if game else None,
		'group(weapons)': weapons_iter if game else None,
		'outfits': game.outfits_iter if game else None,
		'outfits.bones_protection': game.outfits_bones_protection_iter if game else None,
		'outfits.immunities': game.outfits_immunities_iter if game else None,
		'damages': game.damages_iter if game else None,
		'monsters': game.monsters_iter if game else None,
		'monsters.immunities': game.monsters_immunities_iter if game else None,
		}

def csv(gamedata: PathsConfig, localization: str, csv_files_paths: tuple[str], verbose: int, do_import = False, dummy = False):
	'.ltx/.xml import/export from/to .csv file'


	class CsvHeader:

		def __init__(self, game: GameConfig, fields_names: list[str], kind: str | None = None, ltx_file_path: str | None = None):
			self.game, self.fields_names = game, fields_names
			self.kind, self.ltx_file_path = kind, ltx_file_path
			self.ltx = Ltx(ltx_file_path, open_fn=game.paths.open, verbose=game.verbose) if ltx_file_path else None

		def __repr__(self):
			return f'[{self.kind if self.kind else (self.ltx_file_path if self.ltx_file_path else "")}]'

		def get_section(self, section_or_name: Ltx.Section | str) -> Ltx.Section | None:
			if isinstance(section_or_name, Ltx.Section):
				return section_or_name
			if self.ltx:
				return self.ltx.find(section_or_name)
			return self.game.find(section_or_name)

		@classmethod
		def from_table_header(cls, magic: str, fields: list[str]) -> Self:
			'returns class from .csv first line: magic and fields names'
			magic = magic.strip().strip('[').strip(']').strip()
			if magic:
				# [], [.ltx file path], [kind filter]
				if magic.endswith('.ltx'):
					# .ltx file path
					return CsvHeader(game, fields, None, magic)
				else:
					# kind filter
					return CsvHeader(game, fields, magic, None)
			return CsvHeader(game, fields)


	# make info from .db/.xdb gamedata path
	game = GameConfig(gamedata, localization, verbose)

	def iter_csv_file(csv_file_path: str, *, without_values=False) -> Iterator[tuple[CsvHeader, Ltx.Section | str | None, list[str] | None]]:
		'''iters .csv table file row by row
		iters .csv rows (except first .csv line: magic and fields names)
		'''

		def split_values(line: str) -> tuple[str | None, list[str] | None]:
			'returns second and next .csv rows: .ltx section name and it field values'

			def get_buff_char(offset: int) -> str:
				try:
					return buff[i + offset]
				except IndexError:
					return ''

			QUOTE_REPLACE = '\x07'

			def append_value(value: str):
				values.append(value.replace(QUOTE_REPLACE, '"'))

			values = []
			ltx_section_name, _, buff = line.partition(',')
			ltx_section_name = ltx_section_name.strip('[').strip(']').strip()
			if not ltx_section_name:
				return None, None
			if without_values:
				return ltx_section_name, None
			# split values: , or ," or ", or ","
			# with escape "" -> "
			buff = buff.replace('""', QUOTE_REPLACE)
			prev_index = 0
			wait_quote = False
			for i, ch in enumerate(buff):
				if i == 0 and ch == '"':
					wait_quote = True
					prev_index = i + 1
				elif ch == ',':
					if wait_quote:
						if get_buff_char(-1) == '"':
							wait_quote = False
							append_value(buff[prev_index:i-1])
							if get_buff_char(+1) == '"':
								# ","
								wait_quote = True
								prev_index = i + 2
							else:
								# ",
								prev_index = i + 1
					else:
						append_value(buff[prev_index:i])
						if get_buff_char(+1) == '"':
							# ,"
							wait_quote = True
							prev_index = i + 2
						else:
							# ,
							prev_index = i + 1
			if wait_quote:
				append_value(buff[prev_index:-1])
			else:
				append_value(buff[prev_index:])
			return ltx_section_name, values

		if verbose:
			print(f'\tOpen "{csv_file_path}"')

		csv_magic: CsvHeader | None = None
		with open(csv_file_path) as f:
			fields_names: tuple[str] | None = None
			while (line := f.readline()):  # read .csv file line by line
				line = line.strip()
				if csv_magic is None:
					# first line # file format magic [] and fields names
					csv_magic, _, fields_names = line.partition(',')  # split .csv magic and fields names
					fields_names = tuple(map(str.strip, fields_names.split(',')))
					if len(fields_names) < 1:
						raise ValueError(f'Expected: fileds names; has: {line}')
					csv_magic = CsvHeader.from_table_header(csv_magic, fields_names)

					if verbose:
						print(f'\tLtx {csv_magic} fields names: "{", ".join(fields_names)}"')
					
					yield csv_magic, str(csv_magic)+','+','.join(csv_magic.fields_names), None

				else:
					# next lines # .ltx section name and fields values
					ltx_section_name, values = split_values(line)
					if ltx_section_name and ltx_section_name.startswith('#'):  # it comment
						yield csv_magic, ltx_section_name, values
					elif without_values and csv_magic.kind:
						break  # ignore rest non comment lines
					else:
						if ltx_section_name is None and values:  # values without section name
							raise ValueError(f'.ltx section not found: section name {ltx_section_name}')
						yield csv_magic, csv_magic.get_section(ltx_section_name) if ltx_section_name else None, values

		# check for kind filter
		if without_values and csv_magic.kind:
			# iter .ltx sections accordings to kind filter
			if (iter := get_kinds(csv_magic.game).get(csv_magic.kind)):  # iterator for filtered .ltx sections
				if csv_magic.kind.startswith('group('):
					# already grouped and sorted
					for ltx_section in iter():
						yield csv_magic, ltx_section, None
				else:
					# sort by section name
					for ltx_section in sorted(iter(), key=lambda x: x.name):
						yield csv_magic, ltx_section, None

	def get_calc_func(field_name: str) -> tuple[str, Callable] | None:

		def one_div(value: str) -> str:
			if not value:
				return ''
			try:
				return f'{(1 / float(value)):f}'
			except ZeroDivisionError:
				return '0'

		if field_name.startswith('1/'):
			return (field_name[2:], one_div)
		
		return None

	def get_csv_line_from_ltx_section(ltx_section: Ltx.Section, fields_names: tuple[str]) -> str:
		'returns .csv line from .ltx section values; used for export'

		if verbose:
			print(f'Ltx section: [{ltx_section.name}] {ltx_section.ltx.ltx_file_path}')

		ret = f'[{ltx_section.name}]'
		for field_name in fields_names:  # iter fields names from .csv file
			calc_func = get_calc_func(field_name)
			if (calc_func):
				# calculated value by function
				field_name, calc_func = calc_func
			if (field_value := ltx_section.get(field_name)):
				loc = None  # localized field value
				if isinstance(field_value, tuple):
					# list of values # usually numbers/floats list
					field_value = '"' + ', '.join(field_value) + '"'
				elif calc_func:
					# calculated value by function
					field_value_calc = field_value
					field_value = calc_func(field_value)
					if verbose:
						print(f'\t{field_name}={field_value} calculated from {field_value_calc}')
				else:
					# try localize field value
					loc = game.localization.get(field_value)
					if verbose:
						print(f'\t{field_name}={field_value}{" localized: "+loc if loc else ""}')
				# add .ltx field value to .csv line # escape quote if any
				ret += (',' if ret else '') + ('"'+loc.replace('"', '""')+'"' if loc else field_value)
			else:
				ret += ','
		return ret

	def export(csv_file_path: str):
		'export from .ltx files to .csv file'

		if verbose:
			print('Export from .ltx/.xml files to .csv')

		out_buff = ''
		for csv_magic, ltx_section, _ in iter_csv_file(csv_file_path, without_values=True):  # iter .csv lines
			if ltx_section:
				if isinstance(ltx_section, str):
					out_buff += ltx_section
				else:
					# .csv next lines # .csv table values # .ltx section name and .ltx values list
					out_buff += get_csv_line_from_ltx_section(ltx_section, csv_magic.fields_names)
				out_buff += '\n'
			else:
				# empty .csv row # preserve empty rows
				out_buff += ',' * len(csv_magic.fields_names) + '\n'

		# save out buffer to .csv file
		if out_buff:
			with open(csv_file_path, 'w') as f:
				f.write(out_buff)

	def import_(csv_file_path: str):
		'''import from .csv file to .ltx/.xml files
		.csv format:
			first row - .ltx section fields names (second and next columns)
			next rows - .ltx section name (first column); .ltx section fields values (second and next columns)
		'''

		def calc_values(fields_names: tuple[str], values: tuple[str]) -> dict[str, str]:
			'returns fields calculated values is any'
			ret = {}
			for field_name, value in zip(fields_names, values):
				if (calc_func := get_calc_func(field_name)):
					ret[calc_func[0]] = calc_func[1](value)
				else:
					ret[field_name] = value
			return ret

		if verbose:
			print('Import from .csv to .ltx/.xml files')

		for csv_magic, ltx_section, values in iter_csv_file(csv_file_path):  # iter .csv lines
			if isinstance(ltx_section, Ltx.Section):
				# .csv next lines # .csv table values # .ltx section name and .ltx values list
				if verbose:
					print(f'Ltx section: [{ltx_section.name}] {ltx_section.ltx.ltx_file_path}')
				# check .csv table: header with this row
				if len(csv_magic.fields_names) != len(values):  # check .csv table: header and values counts
					raise ValueError(f'.csv file is not table: fields names count {len(csv_magic.fields_names)} not equals line values {values}')
				# save .csv table row to .ltx section
				fields_values = calc_values(csv_magic.fields_names, values)  # join field names (first .csv line) and its values
				if verbose > 1:
					for k, v in fields_values.items():
						print(f'\t{k}={v}')
				if update_section_values(ltx_section, fields_values, game, dummy):  # save .csv table values to .ltx file
					if dummy:
						print(f'\t{csv_file_path} change {ltx_section.ltx.ltx_file_path}')
				if verbose:
					print()

	# main functions
	for csv_file_path in csv_files_paths:
		if verbose:
			print()
		try:
			if do_import:
				import_(csv_file_path)
			else:
				export(csv_file_path)
		except FileNotFoundError as e:
			print(f'File not found: {e}')

def inv(gamedata: PathsConfig, localization: str, images_paths: tuple[str], verbose: int, kind: str | None = None, do_import = False):
	'export/import inventory images from/to equipment .dds according to .ltx section inventory square'

	# make info from .db/.xdb gamedata path
	game = GameConfig(gamedata, localization, max(0, verbose - 1))
	icons = IconsEquipment(game.paths)  # cache a texture

	def export_kind():
		'export images from equipment .dds filtered by .ltx section kind filter'
		if not images_paths:
			return
		kind_path = Path(images_paths[0]) / kind  # export path to export images to
		kind_path.mkdir(parents=True, exist_ok=True)
		if (iter := get_kinds(game).get(kind)):  # get iterator for filtered .ltx sections
			for ltx_section in iter():  # iter .ltx section according to kind filter
				if (image := get_image_by_inv_grid(icons, ltx_section)):  # get inventory image from .ltx section
					out_file_name = str((kind_path / ltx_section.name).absolute()) + '.png'
					image.save(out_file_name)  # save image to export path
					if verbose:
						print(f'Exported {out_file_name}')

	def import_(image_path: str):
		'import image file to equipment .dds file according to .ltx section inventory square'
		image_path = Path(image_path)
		if (image := image_open(image_path.absolute())):  # open image to import
			# copy image to .dds # get inventory square from .ltx section # find .ltx section by name
			if (ltx_section := game.find(image_path.stem)) and (inv_grid := get_inv_grid(ltx_section)):
				icons.set_image(image, inv_grid)

	if verbose:
		print(f'Inventory {"import" if do_import else "export"}: {images_paths}')

	if do_import:
		if images_paths:
			# batch images import to equipment .dds
			for image_path in images_paths:
				import_(image_path)
			# save equipment .dds to gamepath
			icons.save_file(game.paths.gamedata)
			if verbose:
				print('Updated: equipment .dds')
	else:
		export_kind()

def export_equipment(gamedata: PathsConfig, out_paths: tuple[str], verbose: int):
	'export marked equipment .dds to image: grid and grid cell coordinates'

	# make info from .db/.xdb gamedata path
	if not out_paths or not out_paths[0]:
		print(f'Export to image file not specified')
		return
	if verbose:
		print(f'Export equipment as marked grid to "{out_paths[0]}"')
	paths = Paths(gamedata)
	icons = IconsEquipment(paths)
	icons.save_marked_image_from_dds(icons.image, out_paths[0])

def ext_mod_import(gamedata: PathsConfig, localization: str, command: tuple[str], verbose: int):
	'export from another mod: helpers functions'

	# checkings
	if not command or not command[0]:
		print(f'Command for import from another mod not specified')
		return
	if verbose:
		print(f'Import from another mod: {gamedata}')

	def insert_line_into_file(file_path: str, line: bytes, pos: int):
		'inserts line at position into file; append to end: pos = -1'
		if pos == -1:
			# append a new line to file end
			with open(file_path, 'ab') as f:
				f.write(line)
		else:
			# insert a new line into file
			with open(file_path, 'rb') as f:  # read file to buffer
				buff = bytearray(f.read())
			with open(file_path, 'wb') as f:  # write modified buffer to file
				f.write(buff[:pos] + line + buff[pos:])

	match command[0]:

		case 'inv-ltx':
			# show list inventory .ltx sections
			game = GameConfig(gamedata, localization, verbose)
			for ltx_section in game.iter():
				print(f'{ltx_section.ltx.ltx_file_path} [{ltx_section.name}] inv=({ltx_section.get("inv_name")}, {ltx_section.get("inv_grid_x")},{ltx_section.get("inv_grid_y")} {ltx_section.get("inv_grid_width")}x{ltx_section.get("inv_grid_height")}) visual={ltx_section.get("visual")} hud={ltx_section.get("hud")}')

		case 'add-ltx-include':
			# check arguments
			if len(command) < 3:
				print(f'''Command add-ltx-include require 2 arguments: LTX_FILE_PATH INCLUDE_DERECTIVE
Example: add-ltx-include config/weapons/weapons.ltx w_pp19.ltx''')
				return
			# add include directive to .ltx file to #include directives block at file beginning
			ltx_file_path = Path(path_to_os(gamedata.game_path)) / path_to_os(command[1])
			file_path_to_include = command[2].strip('"')
			include_line = b'#include "' + file_path_to_include.encode('cp1251') + b'"\r\n'
			found, line_no, insert_pos = has_include(ltx_file_path, file_path_to_include)
			if found:
				# include found
				if verbose:
					print(f'\tFile included already at line {line_no}: #include "{file_path_to_include}"')
			elif insert_pos is not None:
				# include not found in include block # add include # insert new line at end of include block
				insert_line_into_file(ltx_file_path, include_line, insert_pos)
				if verbose:
					print(f'\tInserted at line {line_no}: #include "{file_path_to_include}"')
			else:
				# include not found in file # add include # append new line to file end
				insert_line_into_file(ltx_file_path, include_line, -1)
				if verbose:
					print(f'\tAppend line {line_no}: #include "{file_path_to_include}"')

def cp_command(src: str, dst: str, patterns: tuple[str], disable_new_check: bool, verbose: int, sync = False, dummy = False):
	'copies gamedata files by glob-like patterns from src to dst path'

	def show_time(time: float) -> str:
		return datetime.fromtimestamp(time).isoformat(sep=' ', timespec='seconds')

	def _copy_file(src: Path, dst: Path):
		if not dummy:
			with src.open('rb') as f_src:
				dst.parent.mkdir(parents=True, exist_ok=True)  # create destination path if not exists
				with dst.open('wb') as f_dst:
					# copy file piece by piece
					while (buff := f_src.read(1024 * 1024)):
						f_dst.write(buff)

	src_path = Path(path_to_os(src))
	dst_path = Path(path_to_os(dst))

	if dummy:
		print('DUMMY RUN !')

	if verbose:
		print(f'src: {src_path}')
		print(f'dst: {dst_path}')

	if sync:
		# sync

		def sync_file(src: Path, dst: Path, gamedata_path: str) -> bool:
			'sync file'

			max_path_len = max(len(x) for x in synced_paths)

			if verbose > 1:
				print(f'\t{gamedata_path}')

			if not src.exists():
				if verbose > 1:
					print(f'\t\tsrc file not exists: {src}')
					print(f'\t\tcopy: {dst} <-')
				else:
					print(f'\t{" "*max_path_len}\t{gamedata_path}')
				_copy_file(dst, src)
				return True

			if not dst.exists():
				if verbose > 1:
					print(f'\t\tdst file not exists: {dst}')
					print(f'\t\tcopy: {src} ->')
				else:
					print(f'\t{gamedata_path}')
				_copy_file(src, dst)
				return True

			stat_src = src.stat()
			stat_dst = dst.stat()
			if stat_src.st_size != stat_dst.st_size:
				# dst and src files has different size
				if verbose > 1:
					print(f'\t\tsizes: {stat_src.st_size}  {stat_dst.st_size}')
			if not disable_new_check:
				if stat_src.st_mtime > stat_dst.st_mtime:
					# src file is newest than dst
					if verbose > 1:
						print(f'\t\tcopy: {src} ->')
						print(f'\t\ttime: {show_time(stat_src.st_mtime)} -> {show_time(stat_dst.st_mtime)}')
					else:
						print(f'\t{gamedata_path}')
					_copy_file(src, dst)
					return True
				elif stat_src.st_mtime < stat_dst.st_mtime:
					# dst file is newest than src
					if verbose > 1:
						print(f'\t\tcopy: {dst} <-')
						print(f'\t\ttime: {show_time(stat_src.st_mtime)} <- {show_time(stat_dst.st_mtime)}')
					else:
						print(f'\t{" "*max_path_len}\t{gamedata_path}')
					_copy_file(dst, src)
					return True
			if verbose > 1:
				print('\t\tSKIP')
			else:
				print(f'\t{gamedata_path:<{max_path_len}} SKIP')
			return False

		if verbose:
			print(f'sync gamedata: {" ".join(map(lambda x: "\""+x+"\"", patterns))}')

		# sync gamedata files
		count = 0
		synced_paths: list[str] = []  # gamepaths
		for pattern in patterns:
			# src files
			for path in sorted((x for x in src_path.glob(path_to_os(pattern)) if x.is_file())):
				gamedata_path = path.relative_to(src_path)
				if str(gamedata_path) in synced_paths:
					continue
				synced_paths.append(str(gamedata_path))
				if sync_file(path, dst_path / gamedata_path, str(gamedata_path)):
					count += 1
			# dst files
			for path in sorted((x for x in dst_path.glob(path_to_os(pattern)) if x.is_file())):
				gamedata_path = path.relative_to(dst_path)
				if str(gamedata_path) in synced_paths:
					continue
				synced_paths.append(str(gamedata_path))
				if sync_file(src_path / gamedata_path, path, str(gamedata_path)):
					count += 1

	else:
		# copy

		def copy_file(src: Path, dst: Path) -> bool:
			'copies file with checkings'

			if not src.exists():
				print(f'\tsrc file not exists: {src}')
				return False

			if verbose:
				print(f'\tcopy: {src.relative_to(src_path)}')

			# check files: size and datetime
			if dst.exists():
				stat_src = src.stat()
				stat_dst = dst.stat()
				if stat_src.st_size != stat_dst.st_size:
					# dst and src files has different size
					print(f'\t\tsize: {stat_src.st_size} -> {stat_dst.st_size}')
				if not disable_new_check and stat_src.st_mtime < stat_dst.st_mtime:
					# dst file is newest than src
					print(f'\t\ttime: {show_time(stat_src.st_mtime)} -> {show_time(stat_dst.st_mtime)}')
					print('\t\tSKIP')
					return False
			# copy file
			_copy_file(src, dst)
			return True

		if verbose:
			print(f'copy gamedata: {" ".join(map(lambda x: "\""+x+"\"", patterns))}')

		# copy gamedata files
		count = 0
		for pattern in patterns:
			for path in src_path.glob(path_to_os(pattern)):
				if copy_file(path, dst_path / path.relative_to(src_path)):
					count += 1

	# show statistics
	if count:
		print(f'copied files: {count}')
	else:
		print('NO FILES WAS COPIED')

def diff_command(gamedata: PathsConfig, localization: str, src: str, dst: str, patterns: tuple[str], verbose: int):
	'diffs gamedata files by glob-like patterns from src to dst path'

	encoding = 'cp1251'
	src_path = Path(path_to_os(src))
	dst_path = Path(path_to_os(dst))

	if verbose:
		print(f'src: {src_path}')
		print(f'dst: {dst_path}')
		print(f'diff gamedata: {" ".join(map(lambda x: "\""+x+"\"", patterns))}')

	def diff_file(src: Path, dst: Path, gamedata_path: str) -> bool:
		'compares two files; returns True if it identical'
		if not src.exists():
			print(f'\tsource file not exists: {gamedata_path}')
		if not dst.exists():
			print(f'\tdestination file not exists: {gamedata_path}')
		try:
			ret = True
			with src.open(encoding=encoding) as fa, dst.open(encoding=encoding) as fb:
				buff_a = fa.readlines()
				buff_b = fb.readlines()
				for line in difflib.unified_diff(buff_a, buff_b, f'src:{src.name}', f'dst:{dst.name}'):
					ret = False  # files different
					stdout.writelines(line)
			return ret
		except FileNotFoundError:
			return False  # files different

	# diff files
	count = diff_count = 0
	for pattern in patterns:
		for path in src_path.glob(path_to_os(pattern)):
			gamedata_path = path.relative_to(src_path)
			count += 1
			if not diff_file(path, dst_path / gamedata_path, gamedata_path):
				diff_count += 1
	print(f'\nfiles: total {count}, different {diff_count}')

if __name__ == '__main__':
	from sys import argv, exit
	import argparse
	from glob import glob

	DEFAULT_CONFIG_PATH = 'brochure.ini'

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''Infographics brochure maker for main game info and gameplay settings.

Used to game developer engagement with gamers.
And game developer tools:
- analyze infographics .html maker for .ltx files; out format: html with embedded images and graphs
- table-based export/import: .ltx/.xml <-> .csv table
- batch inventory images export/import: .dds <-> .png images
- import from another mod: for inventory images use icons utility

Note:
It is not necessary to extract .db/.xdb files to gamedata path. This utility can read all game files from .db/.xdb files !

This utility introduces a new concept for mod authors that consists of two main workflow stages:
- Prepare sources for new mod.
  Misc gamedata files
  - Collect files to gamedata souces path according gamedata-based paths.
  - Create new files.
  Section (.ltx) parameters (numericals and localization text) for .ltx files: ammo, weapons, outfits e.t.c.
  - Collect and edit .ltx sections and/or .ltx files.
  Inventory images
  - Collect and edit .ltx items images as .png separate files. So each inventory item has own .png file with .ltx section name.
    Example: for .ltx [antirad] section: anirad.png.
    Besides, each .ltx inventory item section has grid coordinates for texture .dds as parameters:
	  inv_grid_x, inv_grid_y, inv_grid_width, inv_grid_height.
- Compilation of new mod sources.
  Misc gamedata files
  - Import files to new mod gamedata path.
  Section (.ltx) parameters.
  - Import all .csv tables files to .ltx files.
  Inventory images:
  - Import all .png files into one full-size .dds texture according to .ltx inventory grid: x, y, w, h.

Forkflow for Prepare stage.
  Misc gamedata files
  - Copy files from another mod to gamedata souces path according gamedata-based paths.
    Be kind to gather another mod authors info and show it.
  - Create/edit files by text editor or multimedia editors, examples:
    VS Code for text, Audacity for audio, blender-xray for X-ray graphics, GIMP for .dds and .png images.
  - For 3D objects.
    Copy .ogf files, copy textures .dds files (see .ogf file by hex editor for texture file path and name).
    Add textures to [specification] section of "textures/textures.ltx" file.
  Section (.ltx) parameters.
  - Collect new from another mod and edit existing .ltx files.
    If .ltx file or .ltx section does not exists: create them by text editor. Use latin symbols only.
    Use table-based editor:
	  Export .ltx sections names by rows (first column) and their parameters names by columns (first row) to .csv files.
	  See help for "csv" subcommand.
      Be free to use "--kind" filter to automatically gather of .ltx sections. Or set .ltx file path and sections names.
  Inventory images.
  - Collect new from another mod and edit existing items images as .png separate files.
    Use icons utility to import images from another mod .dds file. See help for "e" subcommand.
  - Select free inventory grid cells for new items.
    Export one full-size .dds to marked image file: grid with cells coordinates. See "-E" option for "inv" subcommand.
  - Edit .ltx files to set .ltx items inventory grid coordinates (and textures names if changed).
    If .ltx file or .ltx section does not exists: create them by text editor. Use latin symbols only.
    Use table-based editor: export .ltx sections to .csv files. See help for "csv" subcommand.

Forkflow for Compilation stage.
  Misc gamedata files
  - Copy files to new mod gamedata path from gamedata souces path according gamedata-based paths.
  Section (.ltx) parameters.
  - Import all table .csv files. See "-i" option for "csv" subcommand.
  Inventory images.
  - Import all table .csv files for inventory grid coordinates. See "-i" option for "csv" subcommand.
  - Import all inventory images by this utility. See help for "inv" subcommand.
''',
				epilog=f'''Examples.

	Make brochure infographics .html file (with embedded images).

Contains localized .ltx sections names with fields names and additional text with images.
So developer can introduce main game info and gameplay settings.

Note: game developer should implement "brochure.ini" file in game folder (where .db/.xdb files).
This file holds various info and brochure settings:
- .html style: default - dark
- .html caption, head title and images, author info footer

For example, "brochure.ini" for SoC (download Stalkercover.jpg from wiki to game folder):
[global]
caption = SoC
author = GSC Game World
localization = rus
style = seaborn
; see: https://plotly.com/python/templates/
; try: ggplot2, seaborn, simple_white, plotly, plotly_white, plotly_dark
[head]
title = S.T.A.L.K.E.R.: Тень Чернобыля
pictures = Stalkercover.jpg

Run from game path (where .db/.xdb files):
{argv[0]} -t 2947ru b > "SoC.html"

Run outside of game path:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru b > "SoC.html"

	For game developers.

	Make analyze infographics .html file (with embedded images and graphs).

Contains .ltx sections names with fields names. Textual info localized. So developer can check main game info.

Make analyse infographics .html page:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru a > "SoC.analyse.html"

	Import/export .ltx sections as table-based .csv files.

Encoding-aware notes.
All .csv files have utf-8 encoding always.
Localized .xml files have self-defined encoding. Do not edit this files by manually. Ltx files already have encoding mess !

Note: be free to increase verbose by -v option.

Export process allows split .ltx fields by number of .csv files to group kind-specific data for ease of use.
For example, split text .ltx fields and power/reliability fields:
- weapons.power.csv for weapons power;
- weapons.names.csv for weapons names;
- weapons.reliability.csv for weapons reliability.

Note: names, descriptions and another textual info usually not mixed with numericals fields in .ltx - because localization problem.
To solve this problem used additional storage: localization .xml files.
Textual info where split into items with own ids and stored in simple structured localization .xml files.
This allows an easy support multi languages mechanism by switching .xml files.
But authors do not recommends to modify localization .xml files manually - it can lead to XML format/encoding errors.

Table .csv table format involve two filters: .ltx sections names and .ltx section fields names:
- first row:
  - first column: file format magic: "[]"
  - next columns: .ltx section fields names
- next rows (can be omitted for --kind automatic filter):
  - first column: .ltx section name
  - next columns: .ltx section fields values

Example of .csv for export .ltx 3 sections with fields: k_dist, k_disp, k_hit:
[],k_dist,k_disp,k_hit
[ammo_11.43x23_fmj],,,
[ammo_11.43x23_hydro],,,
[ammo_12x70_buck],,,

Note: there is calculated fields: 1/.
Example .csv file for weapons.reliability.csv (from .ltx condition_shot_dec field to the count of shots):
[],1/condition_shot_dec

Export process allows automatic define .ltx exported sections by sections kind filter.
This allows automatic export all .ltx sections with fields names (used only .csv first row) for:
{", ".join(get_kinds().keys())}

	Export examples from .db/.xdb files to .csv table file.

Export of selected .ltx sections for selected fields names:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru csv "ammo.names.csv"
ammo.names.csv input file (first line: .ltx field names, next lines: .ltx section names):
[],inv_name_short,inv_name,description
[ammo_11.43x23_fmj],,,
[ammo_5.45x39_ap],,,

Export of all ammo kind .ltx sections for selected fields names:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru csv "ammo.names.csv"
ammo.names.csv input file (first line: kind filter, .ltx field names):
[ammo],inv_name_short,inv_name,description

	Import examples from .csv to gamedata path.

Import from .csv to gamedata path:
{argv[0]} -g ".../S.T.A.L.K.E.R" -t 2947ru csv -i "ammo.names.csv"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', help='game root path (with .db/.xdb files); default: current path')
			parser.add_argument('-t', '--version', metavar='VER', default='2947ru', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			parser.add_argument('-f', '--gamedata', metavar='PATH', default=DEFAULT_GAMEDATA_PATH,
				help=f'gamedata directory path; default: {DEFAULT_GAMEDATA_PATH}')
			parser.add_argument('--exclude-gamedata', action='store_true', help='''exclude files from gamedata sub-path;
used to get original game (.db/.xdb files only) infographics; default: false
''')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; examples: -v, -vv')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('analyse', aliases=('a',), help='analyse: out .html file')
			parser_.add_argument('-c', '--config', metavar='PATH', default=DEFAULT_CONFIG_PATH,
				help=f'config file path; default: {DEFAULT_CONFIG_PATH}')
			parser_ = subparsers.add_parser('brochure', aliases=('b',), help='brochure: out .html file')
			parser_.add_argument('-c', '--config', metavar='PATH', default=DEFAULT_CONFIG_PATH,
				help=f'config file path; default: {DEFAULT_CONFIG_PATH}')
			parser_ = subparsers.add_parser('csv', help='csv: import/export to/from .csv (comma separated values) file')
			parser_.add_argument('-i', '--import', action='store_true', help='import .csv file to gamedata path')
			parser_.add_argument('-D', '--dummy', action='store_true', help='dummy run for import: do not change any file')
			parser_.add_argument('csv', metavar='PATH', nargs='+', help='.csv file path')
			parser_ = subparsers.add_parser('inv',
				help='inv: import/export to/from inventory image files; image files names must equals sections names')
			parser_.add_argument('--kind', choices=(get_kinds().keys()),
				help=f'''export .ltx sections to table .csv file with filter; one from: {", ".join(get_kinds().keys())}; first line: fields names
example .csv file: [],inv_name,inv_name_short,description
''')
			parser_.add_argument('-i', '--import', action='store_true', help='import image file to gamedata path')
			parser_.add_argument('-E', '--equipment', action='store_true',
				help='export full-size .dds to marked image file: grid and grid cell coordinates')
			parser_.add_argument('sections', metavar='PATTERN', nargs='*',
				help='sections names filter pattern; bash name filter: *, ?, [], [!]')
			parser_ = subparsers.add_parser('ext', help='ext: another mod import')
			parser_.add_argument('command', nargs='*', help='import command')
			parser_ = subparsers.add_parser('cp', help='copy files: copy gamedata files from/to mod')
			parser_.add_argument('-T', '--disable-new-check', action='store_true',
				help='disables file time check: copy source file if it newest than destination')
			parser_.add_argument('-N', '--note', help='note: any text; use \n for new line')
			parser_.add_argument('-S', '--src', help='source path: gamedata path')
			parser_.add_argument('-D', '--dst', help='destination path: gamedata path')
			parser_.add_argument('-C', '--sync', action='store_true',
				help='synchronize src and dst files according patterns')
			parser_.add_argument('-M', '--dummy', action='store_true',
				help='dummy run: do not copy any file; used to show changed files')
			parser_.add_argument('patterns', nargs='*', help='files gamedata patterns: glob-like filter')
			parser_ = subparsers.add_parser('diff', help='compare files: text unified diff format')
			parser_.add_argument('-S', '--src', help='source path: gamedata path')
			parser_.add_argument('-D', '--dst', help='destination path: gamedata path')
			parser_.add_argument('patterns', nargs='*', help='files gamedata patterns: glob-like filter')
			return parser.parse_args()

		# parse command-line arguments
		args = parse_args()
		verbose = args.v

		# make game info
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

		# prepare some data for .html infographics
		match args.mode:
			case 'brochure' | 'b' | 'analyse' | 'a':
				config_path = Path(args.config)
				if not config_path.is_absolute():
					config_path = gamepath / config_path
				if not gamepath.exists():
					raise ValueError(f'Game path not found: {args.gamepath}')
				if not config_path.exists():
					raise ValueError(f'Config file not found: {config_path}')

		# run main function
		match args.mode:
			case 'brochure' | 'b':
				# read config
				config = BrochureConfig.from_file(config_path.absolute().resolve())
				brochure(paths_config if paths_config else args.gamedata, config)
			case 'analyse' | 'a':
				# read config
				config = BrochureConfig.from_file(config_path.absolute().resolve())
				analyse(paths_config if paths_config else args.gamedata, config)
			case 'csv':
				# export/import comma separated values .csv as table from/to .ltx files
				csv_files_paths = []
				for csv_path in args.csv:
					csv_path = Path(csv_path)
					if csv_path.is_absolute():
						csv_files_paths.extend(glob(str(csv_path)))
					else:
						csv_files_paths.extend(Path().glob(str(csv_path)))
				csv(paths_config, 'rus', sorted(csv_files_paths), verbose, getattr(args, 'import'), args.dummy)
			case 'inv':
				# export/import inventory images
				if args.equipment:
					# export marked equipment .dds
					export_equipment(paths_config, args.sections, verbose)
				else:
					# batch export/import
					inv(paths_config, 'rus', args.sections, verbose, args.kind, getattr(args, 'import'))
			case 'ext':
				ext_mod_import(paths_config, 'rus', args.command, verbose)
			case 'cp':
				if args.note:
					print(args.note.replace('\\n', '\n'))
				cp_command(args.src, args.dst, args.patterns, args.disable_new_check, verbose, args.sync, args.dummy)
			case 'diff':
				diff_command(paths_config, 'rus', args.src, args.dst, args.patterns, verbose)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
