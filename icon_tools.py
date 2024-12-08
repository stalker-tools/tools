#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker Xray game icons files tool
# Author: Stalker tools, 2023-2024
#
# Python usage example:
# icons = IconsEquipment(gamedata_path)
# icons.get_image(inv_grid_x, inv_grid_y, inv_grid_width, inv_grid_height)  # values inv_grid_* from .ltx section

from collections.abc import Iterator, Iterable
from os.path import join, sep as path_sep
from paths import Paths
from xml.dom.minidom import parse, Element
from io import BytesIO
from base64 import b64encode
from PIL.Image import open as image_open, Image


def get_image_as_html_img(image: Image, format='webp') -> str:
	'return HTML <img> tag with embedded base64 encoded image'
	buff = BytesIO()
	image.save(buff, format=format)
	buff.seek(0)
	return '<img src="data:;base64,{}"/>'.format(b64encode(buff.read()).decode())


class IconsEquipment:
	'Images from <gamedata path>/textures/ui/ui_icon_equipment.dds'

	GRID_SIZE = 50

	def __init__(self, gamedata_path: str) -> None:
		self.gamedata_path = gamedata_path
		self._read_dds()

	def _read_dds(self):
		'load ui_icon_equipment.dds to image in self'
		ui_icon_equipment_filepath = join(self.gamedata_path, 'textures', 'ui', 'ui_icon_equipment.dds')
		self.image = image_open(ui_icon_equipment_filepath)

	def get_image(self, inv_grid_x: int, inv_grid_y: int, inv_grid_width: int, inv_grid_height: int) -> Image:
		'export ui_icon_equipment.dds to image by grid coordinates'
		x, y = inv_grid_x * self.GRID_SIZE, inv_grid_y * self.GRID_SIZE
		return self.image.crop((x, y, x + inv_grid_width * self.GRID_SIZE, y + inv_grid_height * self.GRID_SIZE))


class IconsXmlDds:
	'Pair of .xml texture tags and .dds texture files'

	def __init__(self, xml_file_path: str, dds_file_path: str) -> None:
		self.xml_file_path = xml_file_path
		self.dds_file_path = dds_file_path
		self._read_xml()
		self._read_dds()

	def _read_xml(self):
		'load .xml with texture tags in self'
		self.xml = parse(self.xml_file_path)

	def _read_dds(self):
		'load .dds to image in self'
		self.image = image_open(self.dds_file_path)

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
	def __init__(self, gamedata_path: str) -> None:
		paths = Paths(gamedata_path)
		super().__init__(paths.ui_textures_descr('ui_npc_unique'), paths.ui_textures('ui_npc_unique'))


class UiIconstotal(IconsXmlDds):
	def __init__(self, gamedata_path: str) -> None:
		paths = Paths(gamedata_path)
		super().__init__(paths.ui_textures_descr('ui_iconstotal'), paths.ui_textures('ui_iconstotal'))


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
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
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
		match args.mode:
			case 'equipment' | 'e':
				icons = IconsEquipment(args.gamedata)
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
