
# Main class for Stalker X-ray game config files
# Includes .ltx and .xml localization files
# Author: Stalker tools, 2023-2026

from collections.abc import Iterator, Iterable
from os.path import join
from pickle import load as pickle_load, dump as pickle_dump
from pathlib import Path
# stalker-tools import
from paths import Paths, Config as PathsConfig
from localization import Localization
from ltx_tool import Ltx


class SectionsBase:
	'base class for item-type specific .ltx sections; successor examples: ammo, weapons e.t.c.'

	def __init__(self) -> None:
		self.sections: list[Ltx.Section] = []  # item-type specific sections list
		self.is_loaded = False

	def load_section(self, section: Ltx.Section) -> bool:
		'load section (add to sections list) according to item-type specific filter'
		return False

	def get_localization_files_names(self) -> Iterable[str]: pass  # for inherited class

	def load_localization(self, xml_file_name: str | None = None):
		'load well known .xml localization files from configs/<localization text path>/xml_file_name'
		if xml_file_name:
			self.localization.add_localization_xml_file(join(self.localization.localization_text_path, xml_file_name))

	def iter_value(self, value_name: str) -> Iterator[tuple[str, str, str]]:
		'iterate value with value name for all sections: (section name, localized inv_name_short, value)'
		for section in self.sections:
			if (value := section.get(value_name)) and (inv_name_short := section.get('inv_name_short')):
				# try localize name
				if (buff := self.localization.get(inv_name_short)):
					inv_name_short = buff
				yield section.name, inv_name_short, value


class SectionsRoot:
	'.ltx files root'

	def __init__(self, root_ltx_file_path: str, sections: Iterable[SectionsBase]):
		self.root_ltx_file_path: str = root_ltx_file_path
		self.sections: Iterable[SectionsBase] = sections


class Ammo(SectionsBase):

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_weapons.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'AMMO':
			self.sections.append(section)
			return True
		return False


class Grenade(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if (sname := section.get('class')) and sname.startswith('G_'):
			self.sections.append(section)
			return True
		return False


class Weapons(SectionsBase):

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_weapons.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if (section.get('weapon_class') or section.get('ammo_class')) and not section.name.endswith(('_up', '_up2', '_minigame')):
			self.sections.append(section)
			return True
		return False


class Detectors(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'D_SIMDET':
			self.sections.append(section)
			return True
		return False


class Torchs(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'TORCH_S':
			self.sections.append(section)
			return True
		return False


class Binocles(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'WP_BINOC':
			self.sections.append(section)
			return True
		return False


class Pda(SectionsBase):

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'D_PDA':
			self.sections.append(section)
			return True
		return False


class Outfits(SectionsBase):

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_outfit.xml',)

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

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_equipment.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') in ('II_FOOD', 'II_BOTTL'):
			self.sections.append(section)
			return True
		return False


class Medkit(SectionsBase):

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_equipment.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') in ('II_ANTIR', 'II_MEDKI', 'II_BANDG'):
			self.sections.append(section)
			return True
		return False


class Artefact(SectionsBase):

	def get_localization_files_names(self) -> Iterable[str]:
		return ('st_items_artefacts.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if section.get('class') == 'ARTEFACT':
			self.sections.append(section)
			return True
		return False


class Maps(SectionsBase):
	'Maps (levels): global and levels'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.global_map: Ltx.Section | None = None
		self._maps_names: list[str]  = []
		self.maps: list[Ltx.Section] = []

	def get_localization_files_names(self) -> Iterable[str]:
		return ('string_table_general.xml',)

	def load_section(self, section: Ltx.Section) -> bool:
		if section.name.lower() in self._maps_names:
			self.maps.append(section)
		else:
			match section.name:
				case 'level_maps_single':
					self._maps_names = tuple(x.lower() for x in section.section.keys() if x)
				case 'global_map':
					self.global_map = section
		return self.global_map and len(self.maps) == len(self._maps_names)


class GameConfig:
	'''
	main class for Stalker Xray game config files
	includes .ltx and .xml localization files
	'''

	def __init__(self, config_or_gamedata_path: PathsConfig | str, localization: str, verbose = 0) -> None:
		'localization - gamedata/configs/text/<localization>'
		# set game paths
		self.verbose = verbose
		self.paths = Paths(config_or_gamedata_path)
		cache_path = self.paths.cache_path / 'localization.cache' if not self.paths.gamedata.exists() else None
		self.localization = Localization(self.paths, verbose, cache_file_path=cache_path)
		# init item-type specific lists
		self.ammo = Ammo()
		self.grenade = Grenade()
		self.weapons = Weapons()
		self.detectors = Detectors()
		self.torchs = Torchs()
		self.binocles = Binocles()
		self.pda = Pda()
		self.outfits = Outfits()
		self.damages = Damages()
		self.food = Food()
		self.medkit = Medkit()
		self.artefact = Artefact()
		self.maps = Maps()
		# load .ltx files from root .ltx file
		self.sections_roots: list[SectionsRoot] = []  # .ltx roots files
		self.sections_roots.append(SectionsRoot(self.paths.system_ltx, (
			self.ammo, self.grenade, self.weapons, self.detectors, self.torchs, self.binocles, self.pda,
			self.outfits, self.damages, self.food, self.medkit, self.artefact)))
		self.sections_roots.append(SectionsRoot(join(self.paths.configs, 'game.ltx'), (self.maps,)))
		for sections_root in self.sections_roots:
			self._load_ltx_sections(sections_root)
		self.localization.save_cache(cache_path)

	def _load_ltx_sections(self, sections_root: SectionsRoot):

		def load_localization():
			'loads system.ltx depended .xml localization files'
			if (sections := ltx.sections) and (string_table := sections.get('string_table')) \
					and (files := string_table.get('files')):
				for file in ((files,) if type(files) is str else files):
					self.localization.add_localization_xml_file(join(self.localization.localization_text_path, file + '.xml'))

		def get_cache_file_path() -> Path:
			return Path(self.paths.cache_path) / (sections_root.root_ltx_file_path.replace('\\', '_').replace('/', '_') + '.cache')

		# load from cache if gamedata path not exists
		if not self.paths.gamedata.exists() and get_cache_file_path().exists():
			if self.verbose:
				print(f'Load root .ltx {sections_root.root_ltx_file_path} from cache: {get_cache_file_path()}')
			with open(get_cache_file_path(), 'rb') as f_cache:
				sections = pickle_load(f_cache)
				# copy properties from cache to SectionsBase inherited classes
				for i, s in enumerate(sections):
					for aname in (x for x in s.__dir__() if not x.startswith('_') and not hasattr(getattr(s, x), '__self__')):
						setattr(sections_root.sections[i], aname, getattr(s, aname))
				return

		# try load well-known localization .xml
		for section_base in sections_root.sections:
			if (loc_fnames := section_base.get_localization_files_names()):
				for loc_fname in loc_fnames:
					try:
						self.localization.add_localization_xml_file(join(self.localization.localization_text_path, loc_fname))
					except FileNotFoundError:
						if self.verbose:
							print(f'Localization file not found: {join(self.localization.localization_text_path, loc_fname)}')

		# load root .ltx
		if self.verbose:
			print(f'Load root .ltx: {sections_root.root_ltx_file_path}')
		# load sections from root .ltx
		ltx = Ltx(sections_root.root_ltx_file_path, open_fn=self.paths.open, verbose=self.verbose)
		for section in ltx.iter_sections():
			# load from .ltx for not loaded yet sections
			for section_base in sections_root.sections:  # not loaded sections
				if section_base.load_section(section):
					section_base.is_loaded = True
					continue

		load_localization()

		# update cache if gamedata path not exists
		if not self.paths.gamedata.exists():
			with open(get_cache_file_path(), 'wb') as f_cache:
				pickle_dump(sections_root.sections, f_cache)

	def get_actor_outfit(self) -> Ltx | None:
		ltx_path = join(self.paths.gamedata, 'configs/misc/outfit.ltx')
		self.localization.add_localization_xml_file(join(self.localization.localization_text_path, 'st_items_outfit.xml'))
		return Ltx(ltx_path, False, open_fn=self.paths.open)

	@staticmethod
	def _iter(section_base: SectionsBase) -> Iterator[Ltx.Section]:
		'iterate for all sections'
		if section_base and section_base.sections:
			for section in section_base.sections:
				yield section

	def iter(self) -> Iterator[Ltx.Section]:
		'iterate for all known (loaded) .ltx sections: ammo, weapons e.t.c.'
		for sections_root in self.sections_roots:
			for item in sections_root.sections:
				yield from self._iter(item)

	def find(self, section_name: str, case_insensitive = True) -> Ltx.Section | None:
		'returns section; searchs from cached system.ltx file and all included .ltx files'
		if case_insensitive:
			section_name = section_name.lower()
		for section in self.iter():
			if (section.name.lower() if case_insensitive else section.name) == section_name:
				return section

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
		'''returns localized text by id with different formats since localized text may have formatting
		id - localized text id
		html_format - convert returned text to html code
		localized_only - returns None (instead id) if localized text not found
		'''

		def process_tags(text: str) -> str:
			'returns html code according localized text formatting'
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

		if (buff := self.localization.get(id)):
			# has localization
			if html_format and '%c[' in buff:
				return process_tags(buff)
			return buff
		return None if localized_only else id

	def has_localize(self, id: str) -> bool:
		'returns True if id is .xml localized entry'
		return id in self.localization.string_table

	def find_section_system_ltx(self, section_name: str, case_insensitive = True) -> Ltx.Section | None:
		'returns section; searchs from system.ltx file and all included .ltx files'
		ltx = Ltx(self.paths.system_ltx, True, open_fn=self.paths.open, verbose=self.verbose)
		if case_insensitive:
			section_name = section_name.lower()
		for section in ltx.iter_sections():
			if (section.name.lower() if case_insensitive else section.name) == section_name:
				return section
		return None
