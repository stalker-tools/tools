#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker X-ray game icons files tool
# Author: Stalker tools, 2023-2026

from collections.abc import Iterator
from os.path import join
from pathlib import Path
from xml.dom.minidom import parse, Element
from io import BytesIO
from base64 import b64encode
from PIL.Image import open as image_open, Image
# tools imports
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''
from paths import Paths, Config as PathsConfig, DbFileVersion


def get_image_as_html_img(image: Image, format='webp') -> str:
	'return HTML <img> tag with embedded base64 encoded image'
	buff = BytesIO()
	image.save(buff, format=format)
	buff.seek(0)
	return '<img src="data:;base64,{}"/>'.format(b64encode(buff.read()).decode())


class IconsEquipment:
	'Images from <gamedata path>/textures/ui/ui_icon_equipment.dds'

	GRID_SIZE = 50
	DDS_FILE_PATH = ('textures', 'ui', 'ui_icon_equipment.dds')

	def __init__(self, paths: Paths) -> None:
		self.paths = paths
		self._read_dds()

	def _read_dds(self):
		'load ui_icon_equipment.dds to image in self'
		with self.paths.open(join(*self.DDS_FILE_PATH), 'rb') as f:
			self.image = image_open(f)

	def get_image(self, inv_grid_x: int, inv_grid_y: int, inv_grid_width: int, inv_grid_height: int) -> Image:
		'export ui_icon_equipment.dds to image by grid coordinates'
		x, y = inv_grid_x * self.GRID_SIZE, inv_grid_y * self.GRID_SIZE
		return self.image.crop((x, y, x + inv_grid_width * self.GRID_SIZE, y + inv_grid_height * self.GRID_SIZE))

	def set_image(self, image: Image, inv_grid: tuple[int, int], *, file_path: str | None = None) -> Image:
		'import image to ui_icon_equipment.dds with coordinates according to .ltx section inventory grid square'
		inv_grid = tuple(map(lambda x: x * self.GRID_SIZE, inv_grid))  # convert coordinates from grid to pixels
		self.image.paste(image, inv_grid[:2])  # inv_grid[:2]: works only like that
		if file_path:
			self.save_file(file_path)

	def save_file(self, gamedata_path: str):
		'save equipment .dds to file'
		self.image.save(Path(gamedata_path) / join(*self.DDS_FILE_PATH))

class IconsXmlDds:
	'Pair of .xml texture tags and .dds texture files'

	def __init__(self, paths: Paths, xml_file_path: str, dds_file_path: str) -> None:
		self.paths = paths
		self.xml_file_path = xml_file_path
		self.dds_file_path = dds_file_path
		self._read_xml()
		self._read_dds()

	def _read_xml(self):
		'load .xml with texture tags in self'
		with self.paths.open(self.xml_file_path, 'rb') as f:
			self.xml = parse(f)

	def _read_dds(self):
		'load .dds to image in self'
		with self.paths.open(self.dds_file_path, 'rb') as f:
			self.image = image_open(f)

	def iter_textures(self) -> Iterator[tuple[str, Element]]:
		'iter textures: (id, Element)'
		if (xml := self.xml):
			for t in xml.getElementsByTagName('texture'):
				yield t.getAttribute('id'), t

	def get_rect(self, texture: Element) -> tuple[int, int, int, int] | None:
		try:
			return int(texture.getAttribute('x')), int(texture.getAttribute('y')), int(texture.getAttribute('width')), int(texture.getAttribute('height'))
		except:
			return None

	def _get_image(self, t: Element) -> Image | None:
		if (rect := self.get_rect(t)):
			x, y, w, h = rect
			return self.image.crop((x, y, x + w, y + h))

	def get_image(self, id: str) -> Image | None:
		'get image by id from .dds file'
		for _id, t in self.iter_textures():
			if _id == id:
				return self._get_image(t)
		return None


class UiNpcUnique(IconsXmlDds):
	'NPC icons'

	def __init__(self, paths: Paths) -> None:
		super().__init__(paths, paths.ui_textures_descr('ui_npc_unique'), paths.ui_textures('ui_npc_unique'))


class UiIconstotal(IconsXmlDds):
	'Misc icons: tasks, some characters'

	def __init__(self, paths: Paths) -> None:
		super().__init__(paths, paths.ui_textures_descr('ui_iconstotal'), paths.ui_textures('ui_iconstotal'))


if __name__ == '__main__':
	import argparse
	from sys import argv

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				formatter_class=argparse.RawTextHelpFormatter,
				description='X-ray icons tool. Out format: images',
				epilog=f'''Examples

  Save ui_icon_equipment.dds icon to svd.png:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" e -c 23 30 6 2 -p svd

  Save all icons from ui_iconstotal.xml:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" ui_iconstotal

  Save ui_iconstotal.xml icon to ui_iconsTotal_artefact.png:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" ui_iconstotal -i ui_iconsTotal_artefact
''',
			)
			parser.add_argument('-g', '--gamepath', metavar='PATH', default='.',
				help='game path that contains .db/.xdb files and optional gamedata folder')
			parser.add_argument('-t', '--version', metavar='VER', choices=DbFileVersion.get_versions_names(),
				help=f'.db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: {", ".join(DbFileVersion.get_versions_names())}')
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			parser.add_argument('-v', action='count', default=0, help='verbose mode: 0..; examples: -v, -vv')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('equipment', aliases=('e',), help='icons by ui_icon_equipment.dds')
			parser_.add_argument('-p', metavar='FILENAME', required=True, help='.png filename to save icon to')
			parser_.add_argument('-c', metavar='INT', required=True, type=int, nargs=4, help='grid coordinate from .ltx section: X Y WIDTH HEIGHT')
			parser_ = subparsers.add_parser('ui_npc_unique', help='icons by ui_npc_unique.xml')
			parser_.add_argument('-i', '--id', metavar='TEXT', help='id of icon (all icons if omited)')
			parser_ = subparsers.add_parser('ui_iconstotal', help='icons by ui_iconstotal.xml')
			parser_.add_argument('-i', '--id', metavar='TEXT', help='id of icon (all icons if omited)')
			return parser.parse_args()

		def save_image(id: str, image: Image | None):
			if image:
				file_name = f'{id}.png'
				print(file_name)
				image.save(file_name)

		def save_images(icons: IconsXmlDds, id: str | None):
			if id:
				save_image(id, icons.get_image(id))
			else:
				for id, t in icons.iter_textures():
					save_image(id, icons._get_image(t))

		args = parse_args()
		verbose = args.v
		match args.mode:
			case 'equipment' | 'e':
				if not args.version:
					raise ValueError(f'Argument --version or -t is missing; see help: {argv[0]} -h')
				paths = Paths(PathsConfig(args.gamepath, args.version, args.gamedata, verbose=verbose))
				icons = IconsEquipment(paths)
				if (image := icons.get_image(*args.c)):
					image.save(args.p + '.png')
				else:
					print('Error save to .png')
			case 'ui_npc_unique':
				icons = UiNpcUnique(args.gamedata)
				save_images(icons, args.id)
			case 'ui_iconstotal':
				icons = UiIconstotal(args.gamedata)
				save_images(icons, args.id)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
