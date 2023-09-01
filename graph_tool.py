#!/usr/bin/env python3

from collections.abc import Iterator
from os.path import join
from io import BytesIO
from base64 import b64encode
import matplotlib.pyplot as plt
from ltx_tool import parse_ltx_file, LtxKind, Ltx, LtxFileNotFoundException
from game import Game


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

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

		def get_plot_as_image(fig) -> BytesIO:
			buff = BytesIO()
			fig.savefig(buff, format='png')
			buff.seek(0)
			return buff

		def get_plot_as_html_img(fig) -> str:
			return '<img src="data:;base64,{}"/>'.format(b64encode(get_plot_as_image(fig).read()).decode())

		def analyse(gamedata_path: str):

			def get_value(text: str, type_=float) -> 'type_ | None':
				try:
					return type_(text)
				except:
					return None

			def remove_prefix(name: str, prefix: str) -> str:
				return name[len(prefix):] if name.startswith(prefix) else name

			def get_without_index(name: str) -> str:
				if name and (last_delim_index := name.rfind('_')) > 0:
					return name[:last_delim_index]
				return name

			def get_colors(names: tuple[str]) -> tuple[int]:
				
				def get_next_color():
					nonlocal colors_count
					ret = cycle_colors[colors_count % len(cycle_colors)]
					colors_count += 1
					return ret

				cycle_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
				ret, colors_count = [cycle_colors[0],], 1
				for i, name in enumerate(names[1:]):
					if get_without_index(name) != get_without_index(names[i]):
						ret.append(get_next_color())
					else:
						ret.append(ret[-1])
				return ret

			def damages(value_name: str) -> Iterator[tuple[str, float]]:
				ltx_path = join(gamedata_path, 'configs/creatures/damages.ltx')
				try:
					for x in parse_ltx_file(ltx_path):
						match x[0]:
							case LtxKind.LET:
								if x[3] == value_name:
									if (value := get_value(x[4][0])) is not None:
										yield remove_prefix(x[2], 'stalker_'), value
				except LtxFileNotFoundException:
					pass

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

			def print_plot(data, title, value_name, xlabel, log_scale=False):
				if data:
					fig, ax = plt.subplots()
					names = tuple((f'{x[0]} {i+1}' for i, x in enumerate(data)))
					y_pos = range(len(data))
					plt.barh(y_pos, tuple(map(lambda x: x[1], data)), height=.5, linewidth=0.1, color=get_colors(names))
					ax.invert_yaxis()
					plt.yticks(y_pos, labels=names)
					ax.grid(axis='x', linestyle='dashed')
					ax.set_title(title)
					ax.set_xlabel(f'{value_name} {xlabel}')
					if log_scale:
						ax.set_xscale('log')
					fig.set_size_inches((4.5, len(names) / 3))
					fig.tight_layout()
					print(get_plot_as_html_img(fig))
					plt.close()

			def damages_html(value_name='hit_fraction', title='NPC stalkers vulnerability', xlabel='(less is stronger)'):
				a = sorted(tuple((name, damage) for name, damage in damages(value_name)), key=lambda x: x[0])
				print_plot(a, title, value_name, xlabel)

			def get_table(iter_finction):
				sections = []
				table: list[tuple[str]] = []
				# get ltx sections
				for section in sorted((x for x in iter_finction()), key=lambda section: section.name):
					if (inv_name_short := game.localize(section.get('inv_name_short'))):
						sections.append(section)
						table.append((section.name, inv_name_short, game.localize(section.get("description"))))
				print_table(table)
				return sections

			def get_float_value(value: str | tuple[str]) -> float:
				if value:
					return float(value[0] if type(value) is tuple else value)
				return 0

			def actor_outfit_table() -> list[Ltx.Section]:
				return get_table(game.outfits_iter)

			def actor_outfit_html(value_name='hit_fraction_actor', title='Actor outfit vulnerability', xlabel='(less is stronger)'):
				a = tuple((section.name, get_float_value(section.get(value_name))) for section in sections)
				print_plot(a, title, value_name, xlabel)

			def amunition_table() -> list[Ltx.Section]:
				return get_table(game.ammo_iter)

			def amunition_html(value_name='k_hit', title='Amunition power', xlabel='($1 = 300 J$) (more is stronger)', log_scale=False):
				a = tuple((section.name, get_float_value(section.get(value_name))) for section in sections)
				print_plot(a, title, value_name, xlabel, log_scale)

			def weapons_table(ef_weapon_type: str) -> list[Ltx.Section]:
				def pistol_iter():
					for section in game.weapons_iter():
						if section.name == 'wpn_pb':
							pass
						if ef_weapon_type == section.get('ef_weapon_type'):
							yield section
				return get_table(pistol_iter)

			def weapons_html(value_name='hit_power', title='Weapon power', xlabel='(more is stronger)', log_scale=False):
				a = tuple((section.name, get_float_value(section.get(value_name))) for section in sections)
				print_plot(a, title, value_name, xlabel, log_scale)

			print(f'<h1>{args.head}<h1><hr/>')

			game = Game(gamedata_path, args.localization)

			print('<h2>1 Actor tactical parameters</h2>')
			sections = actor_outfit_table()
			actor_outfit_html()
			actor_outfit_html('strike_protection')
			actor_outfit_html('explosion_protection')
			actor_outfit_html('fire_wound_protection')
			actor_outfit_html('wound_protection')
			actor_outfit_html('radiation_protection')
			actor_outfit_html('telepatic_protection')
			actor_outfit_html('burn_protection')
			actor_outfit_html('shock_protection')
			actor_outfit_html('chemical_burn_protection')

			print('<h2>2 NPC tactical parameters</h2>')
			damages_html()

			print('<h2>3 Ammunition tactical parameters</h2>')
			sections = amunition_table()
			amunition_html()
			amunition_html('k_impulse', xlabel='(more is stronger)')
			amunition_html('k_pierce', xlabel='(more is stronger)', log_scale=True)
			amunition_html('k_ap', xlabel='(more is stronger)', log_scale=True)
			amunition_html('k_dist', 'Amunition accuracy', '(more is longer range)')
			amunition_html('k_disp', 'Amunition accuracy', '(more is less accurately)')
			amunition_html('k_air_resistance', 'Amunition range', '')

			print('<h2>4 Weapon tactical parameters</h2>')
			for index, (ef_weapon_type, text) in enumerate((('5', 'pistols'), ('6', 'assault rifles'), ('7', 'rifles'), ('8', 'guns'))):
				print(f'<h3>4.{index + 1} {text}</h3>')
				sections = weapons_table(ef_weapon_type)
				weapons_html()
				weapons_html('hit_impulse', 'Weapon hit impulse', '(more is stronger)', True)
				weapons_html('bullet_speed', 'Weapon bullet speed', ', m/s', True)
				weapons_html('fire_distance', 'Weapon fire distance', 'max, m', True)
				print(f'<h4>4.{index + 1}.1 Weapon accuracy: {text}</h2>')
				weapons_html('hit_probability_gd_novice', 'Weapon accuracy', '(more is more accurate)')
				weapons_html('fire_dispersion_condition_factor', 'Weapon accuracy', '(less is more accurate)')
				print(f'<h4>4.{index + 1}.2 Weapon reliability: {text}</h2>')
				weapons_html('condition_shot_dec', 'Weapon reliability', '(less is more reliable)', True)
				weapons_html('misfire_condition_k', 'Weapon misfire', '(less is more reliable)')
				weapons_html('misfire_probability', 'Weapon misfire', '(less is more reliable)', True)

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
