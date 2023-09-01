
from collections.abc import Iterator
from os.path import join, basename
from glob import glob
# tools imports
from ltx_tool import Ltx, parse_ltx_file, LtxKind
from xml_tool import add_localization_dict_from_localization_xml_file


class SectionsBase:

	def __init__(self, gamedata_path: str, configs_path: str, localization_text_path: str, localization_dict: dict) -> None:
		self.gamedata_path, self.configs_path, self.localization_text_path = gamedata_path, configs_path, localization_text_path
		self.localization_dict = localization_dict
		self.sections: list[Ltx.Section] = []

	def load_section(self, section: Ltx.Section) -> bool:
		return False

	def load_localization(self):
		'loads well known .xml localization files'
		pass

	def iter_value(self, value_name: str) -> Iterator[tuple[str, str, str]]:
		for section in self.sections:
			if (value := section.get(value_name)) and (inv_name_short := section.get('inv_name_short')):
				# try localize name
				if (buff := self.localization_dict.get(inv_name_short)):
					inv_name_short = buff
				yield section.name, inv_name_short, value


class Ammo(SectionsBase):

	def load_localization(self):
		add_localization_dict_from_localization_xml_file(self.localization_dict, self.configs_path, join(self.localization_text_path, 'st_items_weapons.xml'))

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'AMMO':
			self.sections.append(section)
			return True
		return False


class Weapons(SectionsBase):

	def load_localization(self):
		add_localization_dict_from_localization_xml_file(self.localization_dict, self.configs_path, join(self.localization_text_path, 'st_items_weapons.xml'))

	def load_section(self, section: Ltx.Section) -> bool:
		if (section.get('weapon_class') or section.get('ammo_class')) and not section.name.endswith(('_up', '_up2', '_minigame')):
			self.sections.append(section)
			return True
		return False


class Outfits(SectionsBase):

	def load_localization(self):
		add_localization_dict_from_localization_xml_file(self.localization_dict, self.configs_path, join(self.localization_text_path, 'st_items_outfit.xml'))

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'E_STLK':
			self.sections.append(section)
			return True
		return False


class Game:

	def __init__(self, gamedata_path: str, localization: str) -> None:
		self.gamedata_path = gamedata_path
		self.configs_path = join(gamedata_path, 'configs')
		self.localization_text_path = join(self.configs_path, 'text', localization)
		self.localization_dict = {}
		self.ammo = Ammo(self.gamedata_path, self.configs_path, self.localization_text_path, self.localization_dict)
		self.ammo.load_localization()
		self.weapons = Weapons(self.gamedata_path, self.configs_path, self.localization_text_path, self.localization_dict)
		self.weapons.load_localization()
		self.outfits = Outfits(self.gamedata_path, self.configs_path, self.localization_text_path, self.localization_dict)
		self.outfits.load_localization()
		self.load_ltx_sections((self.ammo, self.weapons, self.outfits))

	def load_ltx_sections(self, section_bases: list[SectionsBase]):

		def load_localization():
			'loads system.ltx depended .xml localization files'
			if (sections := ltx.sections) and (string_table := sections.get('string_table')) \
					and (files := string_table.get('files')):
				for file in ((files,) if type(files) is str else files):
					add_localization_dict_from_localization_xml_file(self.localization_dict, self.configs_path, join(self.localization_text_path, file + '.xml'), True)

		ltx = Ltx(join(self.configs_path, 'system.ltx'))
		for section in ltx.iter_sections():
			for section_base in section_bases:
				if section_base.load_section(section):
					continue

		load_localization()

	def get_actor_outfit(self) -> Ltx | None:
		ltx_path = join(self.gamedata_path, 'configs/misc/outfit.ltx')
		add_localization_dict_from_localization_xml_file(self.localization_dict, self.configs_path, join(self.localization_text_path, 'st_items_outfit.xml'))
		return Ltx(ltx_path, False)

	@staticmethod
	def _iter(section_base):
		if section_base and section_base.sections:
			for section in section_base.sections:
				yield section

	def ammo_iter(self) -> Iterator[Ltx.Section]:
		yield from self._iter(self.ammo)

	def weapons_iter(self) -> Iterator[Ltx.Section]:
		yield from self._iter(self.weapons)

	def outfits_iter(self) -> Iterator[Ltx.Section]:
		yield from self._iter(self.outfits)

	def localize(self, id: str) -> str | None:
		if self.localization_dict:
			return self.localization_dict.get(id, id)
		return id
