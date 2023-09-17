
from os.path import join, sep as path_sep
from xml.dom.minidom import parse, Element
from io import BytesIO
from base64 import b64encode
from PIL.Image import open


def get_image_as_html_img(image) -> str:
	buff = BytesIO()
	image.save(buff, format='png')
	buff.seek(0)
	return '<img src="data:;base64,{}"/>'.format(b64encode(buff.read()).decode())


class IconsTotal:

	def __init__(self, gamedata_path: str) -> None:
		self.gamedata_path = gamedata_path
		self._read_dds()

	def _read_dds(self) -> 'Image':
		'export ui_iconstotal.xml to .png picture'
		self.image, self.textures = None, None
		ui_iconstotal_filepath = join(self.gamedata_path, 'configs', 'ui', 'textures_descr', 'ui_iconstotal.xml')
		textures_path = join(self.gamedata_path, 'textures')
		try:
			if (_xml := parse(ui_iconstotal_filepath)) and (files := _xml.getElementsByTagName('file')) and \
					(file_name := files[0].getAttribute('name')) and \
					(textures := _xml.getElementsByTagName('texture')):
				img_file_path = join(textures_path, file_name.replace('\\', path_sep) + '.dds')
				self.image, self.textures = open(img_file_path), textures
		except: pass

	def _get_image(self, texture: Element) -> 'tuple[str, Image] | None':
		if (id := texture.getAttribute('id')):
			x = int(texture.getAttribute('x'))
			y = int(texture.getAttribute('y'))
			width = int(texture.getAttribute('width'))
			height = int(texture.getAttribute('height'))
			return (id, self.image.crop((x, y, x + width, y + height)))
		return None

	def get_image(self, id: str) -> 'Image | None':
		if self.textures and self.image:
			for texture in self.textures:
				try:
					if (_id := texture.getAttribute('id')) and _id == id:
						return self._get_image(texture)[1]
				except Exception as e:
					print(f'Error: {e}')
		return None

	def iter_images(self):
		if self.textures:
			for texture in self.textures:
				yield self._get_image(texture)


class IconsEquipment:

	GRID_SIZE = 50

	def __init__(self, gamedata_path: str) -> None:
		self.gamedata_path = gamedata_path
		self._read_dds()

	def _read_dds(self) -> 'Image':
		'get ui_icon_equipment.dds'
		ui_icon_equipment_filepath = join(self.gamedata_path, 'textures', 'ui', 'ui_icon_equipment.dds')
		self.image = open(ui_icon_equipment_filepath)

	def get_image(self, inv_grid_x: int, inv_grid_y: int, inv_grid_width: int, inv_grid_height: int) -> 'Image':
		'export ui_icon_equipment.dds to .png picture by grid coordinates'
		x, y = inv_grid_x * self.GRID_SIZE, inv_grid_y * self.GRID_SIZE
		return self.image.crop((x, y, x + inv_grid_width * self.GRID_SIZE, y + inv_grid_height * self.GRID_SIZE))


if __name__ == '__main__':
	import argparse
	from sys import argv

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				formatter_class=argparse.RawTextHelpFormatter,
				description='X-ray icons tool. Out format: images',
				epilog=f'''Examples

  Save ui_iconstotal.xml icon to ui_iconsTotal_artefact.png:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" t -i ui_iconsTotal_artefact

  Save all ui_iconstotal.xml icons to .png files:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" t

  Save ui_icon_equipment.dds icon to svd.png:
{argv[0]} -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" e -c 23 30 6 2 -p svd''',
			)
			parser.add_argument('-f', '--gamedata', metavar='PATH', required=True, help='gamedata directory path')
			parser.add_argument('-l', '--localization', metavar='LANG', default='rus', help='localization language (see gamedata/configs/text path): rus (default), cz, hg, pol')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('total', aliases=('t',), help='icons by ui_iconstotal.xml')
			parser_.add_argument('-i', '--id', metavar='TEXT', help='id of icon (all icons if omited)')
			parser_ = subparsers.add_parser('equipment', aliases=('e',), help='icons by ui_icon_equipment.dds')
			parser_.add_argument('-p', metavar='FILENAME', required=True, help='.png filename to save icon to')
			parser_.add_argument('-c', metavar='INT', required=True, type=int, nargs=4, help='grid coordinate from .ltx section: X Y WIDTH HEIGHT')
			return parser.parse_args()

		args = parse_args()
		match args.mode:
			case 'total' | 't':
				icons = IconsTotal(args.gamedata)
				if args.id:
					if (image := icons.get_image(args.id)):
						image.save(args.id + '.png')
					else:
						print(f'Error: ID not exists "{args.id}"')
				else:
					# save all icons
					for id, image in icons.iter_images():
						image.save(id + '.png')
			case 'equipment' | 'e':
				icons = IconsEquipment(args.gamedata)
				if (image := icons.get_image(*args.c)):
					image.save(args.p + '.png')
				else:
					print('Error save to .png')

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
