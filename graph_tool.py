#!/usr/bin/env python3

from collections.abc import Iterator
from os.path import join, basename
from glob import glob
from io import BytesIO
from base64 import b64encode
import matplotlib.pyplot as plt
from ltx_tool import parse_ltx_file, LtxKind


if __name__ == '__main__':
	import argparse
	from sys import argv, exit

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='X-ray .ltx file parser',
				epilog=f'Examples: {argv[0]} -f 1.ltx 2.ltx',
			)
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
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
				if (last_delim_index := name.rfind('_')) > 0:
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
				for x in parse_ltx_file(ltx_path):
					match x[0]:
						case LtxKind.LET:
							if x[3] == value_name:
								if (value := get_value(x[4][0])) is not None:
									yield remove_prefix(x[2], 'stalker_'), value

			def amunition(value_name: str) -> Iterator[tuple[str, float]]:
				ltx_path = join(gamedata_path, 'configs/weapons/weapons.ltx')
				for x in parse_ltx_file(ltx_path):
					match x[0]:
						case LtxKind.LET:
							if x[3] == value_name:
								if (value := get_value(x[4][0])) is not None:
									yield remove_prefix(x[2], 'ammo_'), value

			def weapons(value_name) -> Iterator[tuple[str, float]]:
				for ltx_path in glob(join(gamedata_path, 'configs/weapons/w_*.ltx')):
					if any(excl in ltx_path for excl in ('mounted', 'knife', 'binoc')):
						continue
					name = remove_prefix(basename(ltx_path), 'w_')[:-4]
					for x in parse_ltx_file(ltx_path):
						match x[0]:
							case LtxKind.LET:
								if x[3] == value_name:
									if (value := get_value(x[4][0])) is not None:
										yield name, value

			def damages_html(value_name='hit_fraction', title='NPC stalkers vulnerability', xlabel='(less is stronger)'):
				fig, ax = plt.subplots()
				a = sorted(tuple((name, damage) for name, damage in damages(value_name)), key=lambda x: x[0])
				names = tuple(map(lambda x: x[0], a))
				y_pos = range(len(a))
				plt.barh(y_pos, tuple(map(lambda x: x[1], a)), height=.5, linewidth=0.1, color=get_colors(names))
				ax.invert_yaxis()
				plt.yticks(y_pos, labels=names)
				ax.grid(axis='x', linestyle = 'dashed')
				ax.set_title(title)
				ax.set_xlabel(f'{value_name} {xlabel}')
				fig.set_size_inches((5, len(names) / 4))
				fig.tight_layout()
				print(get_plot_as_html_img(fig))

			def amunition_html(value_name='k_hit', title='Amunition power', xlabel='($1 = 300 J$) (more is stronger)'):
				fig, ax = plt.subplots()
				a = sorted(tuple((name, damage) for name, damage in amunition(value_name)), key=lambda x: x[0])
				names = tuple(map(lambda x: x[0], a))
				y_pos = range(len(a))
				plt.barh(y_pos, tuple(map(lambda x: x[1], a)), height=.5, linewidth=0.1, color=get_colors(names))
				ax.invert_yaxis()
				plt.yticks(y_pos, labels=names)
				ax.grid(axis='x', linestyle = 'dashed')
				ax.set_title(title)
				ax.set_xlabel(f'{value_name} {xlabel}')
				fig.set_size_inches((5, len(names) / 4))
				fig.tight_layout()
				print(get_plot_as_html_img(fig))

			def weapons_html(value_name='hit_power', title='Weapon power', xlabel='(more is stronger)', log_scale=False):
				fig, ax = plt.subplots()
				a = sorted(tuple((n, v) for n, v in weapons(value_name)), key=lambda x: x[0])
				names = tuple(map(lambda x: x[0], a))
				y_pos = range(len(a))
				plt.barh(y_pos, tuple(map(lambda x: x[1], a)), height=.5, linewidth=0.1, color=get_colors(names))
				ax.invert_yaxis()
				plt.yticks(y_pos, labels=names)
				ax.grid(axis='x', linestyle = 'dashed')
				ax.set_title(f'{title}')
				ax.set_xlabel(f'{value_name} {xlabel}')
				if log_scale:
					ax.set_xscale('log')
				fig.set_size_inches((5, len(names) / 4))
				fig.tight_layout()
				print(get_plot_as_html_img(fig))

			print(f'<h1>{args.head}<h1><hr/>')
			print('<h2>1 NPC tactical parameters</h2>')
			damages_html()
			print('<h2>2 Ammunition tactical parameters</h2>')
			amunition_html()
			print('<h2>3 Weapon tactical parameters</h2>')
			weapons_html()
			weapons_html('hit_impulse', 'Weapon hit impulse', '(more is stronger)', True)
			weapons_html('bullet_speed', 'Weapon bullet speed', ', m/s', True)
			weapons_html('fire_distance', 'Weapon fire distance', 'max, m', True)
			print('<h2>4 Weapon accuracy</h2>')
			weapons_html('hit_probability_gd_novice', 'Weapon accuracy', '(more is more accurate)')
			weapons_html('fire_dispersion_condition_factor', 'Weapon accuracy', '(less is more accurate)')
			print('<h2>5 Weapon reliability</h2>')
			weapons_html('condition_shot_dec', 'Weapon reliability', '(less is more reliable)', True)
			weapons_html('misfire_condition_k', 'Weapon misfire', '(less is more reliable)')
			weapons_html('misfire_probability', 'Weapon misfire', '(less is more reliable)', True)

		analyse(args.gamedata)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
