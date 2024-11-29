
from typing import Iterable
from os.path import join, abspath, sep
from pathlib import Path


class Paths:

	def __init__(self, gamedata_path: str) -> None:
		self.gamedata = abspath(gamedata_path)
		if (p := Path(join(self.gamedata, 'configs'))) and p.exists():
			self.configs = p.absolute()
		elif (p := Path(join(self.gamedata, 'config'))) and p.exists():
			self.configs = p.absolute()
		else:
			raise FileExistsError(f'Stalker configs path not exisists: {gamedata_path}')

	def __str__(self) -> str:
		return f'Paths({self.gamedata})'

	@classmethod
	def join(cls, *paths: Iterable[str]) -> str:
		'cross-platform path join'
		if sep != '\\':
			return join(*(x.replace('\\', sep) for x in paths))
		return join(*paths)

	# Well-known paths

	@property
	def game(self) -> str:
		'returns game root path'
		return abspath(join(self.gamedata, '..'))

	@property
	def system_ltx(self) -> str:
		'returns system.ltx file path'
		return join(self.configs, 'system.ltx')

	@property
	def game_ltx(self) -> str:
		'returns game.ltx file path'
		return join(self.configs, 'game.ltx')

	def relative(self, path: str) -> str:
		'return relative path to gamedata'
		p = Path(path)
		if not p.is_relative_to(self.gamedata):
			return path
		return str(p.relative_to(self.gamedata))

	def ui_textures_descr(self, common_name: str) -> str:
		'return UI textures .xml file path: <gamedata path>/configs/ui/textures_descr/.xml'
		return join(self.configs, 'ui', 'textures_descr', f'{common_name}.xml')

	def ui_textures(self, common_name: str) -> str:
		'return UI textures .dds file path: <gamedata path>/textures/ui/.dds'
		return join(self.gamedata, 'textures', 'ui', f'{common_name}.dds')
