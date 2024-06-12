
from os.path import join
from pathlib import Path


class Paths:

	def __init__(self, gamedata_path: str) -> None:
		self.gamedata = gamedata_path

	def __str__(self) -> str:
		return f'Paths({self.gamedata})'

	# Well-known paths

	@property
	def configs(self) -> str:
		return join(self.gamedata, 'configs')

	@property
	def system_ltx(self) -> str:
		return join(self.gamedata, 'configs', 'system.ltx')

	def relative(self, path: str) -> str:
		'return relative path to gamedata'
		p = Path(path)
		if not p.is_relative_to(self.gamedata):
			return path
		return str(p.relative_to(self.gamedata))

	def ui_textures_descr(self, common_name: str) -> str:
		'return UI textures .xml file path: <gamedata path>/configs/ui/textures_descr/.xml'
		return join(self.gamedata, 'configs', 'ui', 'textures_descr', f'{common_name}.xml')

	def ui_textures(self, common_name: str) -> str:
		'return UI textures .dds file path: <gamedata path>/textures/ui/.dds'
		return join(self.gamedata, 'textures', 'ui', f'{common_name}.dds')
