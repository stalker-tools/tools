
# Main class for Stalker Xray game config files
# Includes .ltx and .xml localization files
# Author: Stalker tools, 2023-2024

from collections.abc import Iterator
from os.path import join
# tools imports
from paths import Paths, Config as PathsConfig
from localization import Localization
from ltx_tool import Ltx


class SectionsBase:
	'base class for item-type specific .ltx sections; successor examples: ammo, weapons e.t.c.'

	def __init__(self, paths: Paths, localization: Localization) -> None:
		self.paths = paths
		self.localization: Localization = localization
		self.sections: list[Ltx.Section] = []  # item-type specific sections list

	def load_section(self, section: Ltx.Section) -> bool:
		'load section (add to sections list) according to item-type specific filter'
		return False

	def load_localization(self, xml_file_name: str | None = None):
		'load well known .xml localization files from configs/<localization text path>/xml_file_name'
		if xml_file_name:
			self.localization.add_localization_xml_file(join(self.localization.localization_text_path, xml_file_name))

	def iter_value(self, value_name: str) -> Iterator[tuple[str, str, str]]:
		'iterate value with value name for all sections: (section name, localized inv_name_short, value)'
		for section in self.sections:
			if (value := section.get(value_name)) and (inv_name_short := section.get('inv_name_short')):
				# try localize name
				if (buff := self.localization.string_table.get(inv_name_short)):
					inv_name_short = buff
				yield section.name, inv_name_short, value


class Ammo(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_weapons.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'AMMO':
			self.sections.append(section)
			return True
		return False


class Weapons(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_weapons.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if (section.get('weapon_class') or section.get('ammo_class')) and not section.name.endswith(('_up', '_up2', '_minigame')):
			self.sections.append(section)
			return True
		return False


class Outfits(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_outfit.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'E_STLK':
			self.sections.append(section)
			return True
		return False


class Damages(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('hit_fraction') is not None:
			self.sections.append(section)
			return True
		return False


class Food(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_equipment.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') in ('II_FOOD', 'II_BOTTL'):
			self.sections.append(section)
			return True
		return False


class Medkit(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_equipment.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') in ('II_ANTIR', 'II_MEDKI', 'II_BANDG'):
			self.sections.append(section)
			return True
		return False


class Artefact(SectionsBase):

	def load_localization(self):
		super().load_localization('st_items_artefacts.xml')

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'ARTEFACT':
			self.sections.append(section)
			return True
		return False


class GameConfig:
	'''
	main class for Stalker Xray game config files
	includes .ltx and .xml localization files
	'''

	def __init__(self, config_or_gamedata_path: PathsConfig | str, localization: str, verbose = True) -> None:
		'localization - gamedata/configs/text/<localization>'
		# set game paths
		self.verbose = verbose
		self.paths = Paths(config_or_gamedata_path)
		self.localization = Localization(self.paths)
		# init item-type specific lists
		self.ammo = Ammo(self.paths, self.localization)
		self.weapons = Weapons(self.paths, self.localization)
		self.outfits = Outfits(self.paths, self.localization)
		self.damages = Damages(self.paths, self.localization)
		self.food = Food(self.paths, self.localization)
		self.medkit = Medkit(self.paths, self.localization)
		self.artefact = Artefact(self.paths, self.localization)
		self._items = (self.ammo, self.weapons, self.outfits, self.damages, self.food, self.medkit, self.artefact)
		self.load_ltx_sections(self._items)

	def load_ltx_sections(self, section_bases: list[SectionsBase]):

		def load_localization():
			'loads system.ltx depended .xml localization files'
			if (sections := ltx.sections) and (string_table := sections.get('string_table')) \
					and (files := string_table.get('files')):
				for file in ((files,) if type(files) is str else files):
					self.localization.add_localization_xml_file(join(self.localization.localization_text_path, file + '.xml'))

		for section_base in section_bases:
			section_base.load_localization()

		ltx = Ltx(self.paths.system_ltx, open_fn=self.paths.open)
		for section in ltx.iter_sections():
			for section_base in section_bases:
				if section_base.load_section(section):
					continue

		load_localization()

	def get_actor_outfit(self) -> Ltx | None:
		ltx_path = join(self.paths.gamedata, 'configs/misc/outfit.ltx')
		self.localization.add_localization_xml_file(join(self.localization.localization_text_path, 'st_items_outfit.xml'))
		return Ltx(ltx_path, False, open_fn=self.paths.open)

	@staticmethod
	def _iter(section_base) -> Iterator[Ltx.Section]:
		'iterate for all sections'
		if section_base and section_base.sections:
			for section in section_base.sections:
				yield section

	def iter(self) -> Iterator[Ltx.Section]:
		'iterate for all known sections: ammo, weapons e.t.c.'
		for item in self._items:
			yield from self._iter(item)

	def ammo_iter(self) -> Iterator[Ltx.Section]:
		'iterate for ammunition sections'
		yield from self._iter(self.ammo)

	def weapons_iter(self) -> Iterator[Ltx.Section]:
		'iterate for weapons sections'
		yield from self._iter(self.weapons)

	def outfits_iter(self) -> Iterator[Ltx.Section]:
		'iterate for outfits sections'
		yield from self._iter(self.outfits)

	def damages_iter(self) -> Iterator[Ltx.Section]:
		yield from self._iter(self.damages)

	def food_iter(self) -> Iterator[Ltx.Section]:
		'iterate for food sections'
		yield from self._iter(self.food)

	def medkit_iter(self) -> Iterator[Ltx.Section]:
		'iterate for medkits sections'
		yield from self._iter(self.medkit)

	def artefact_iter(self) -> Iterator[Ltx.Section]:
		'iterate for artefacts sections'
		yield from self._iter(self.artefact)

	def localize(self, id: str, html_format = False, localized_only = False) -> str | None:

		def process_tags(text: str) -> str:
			COLOR_TAG = '%c['
			COLOR_TAG_DEFAULT = '%c[default]'
			ret = text.replace('\\n', '<br/>')
			ret = ret.replace(COLOR_TAG_DEFAULT, '</span>')
			while (start_index := ret.find(COLOR_TAG)) >= 0:
				if (end_index := ret.find(']', start_index)):
					colors = tuple(map(int, ret[start_index + len(COLOR_TAG):end_index].split(',', 4)))
					if len(colors) != 4:
						break
					ret = ret[:start_index] + f'</span><span style="color:#{colors[0]:02x}{colors[1]:02x}{colors[3]:02x};">' + ret[end_index + 1:]
				else:
					break
			return ret

		if (buff := self.localization.string_table.get(id, None if localized_only else id)):
			# has localization
			if html_format and '%c[' in buff:
				return process_tags(buff)
			return buff
		return None if localized_only else id

	def has_localize(self, id: str) -> bool:
		'returns True if id is .xml localized entry'
		return id in self.localization.string_table
