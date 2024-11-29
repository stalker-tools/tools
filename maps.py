
from collections.abc import Iterator
# tools imports
from paths import Paths
from ltx_tool import Ltx
from PIL.Image import open as image_open, Image


class Maps:

	def __init__(self, gamedata_path: str) -> None:
		self.paths = Paths(gamedata_path)
		self.global_map: Ltx.Section | None = None
		self.maps: tuple[Ltx.Section] | None = None
		self.load_maps()

	def iter_sections(self, ltx: Ltx) -> Iterator[Ltx.Section]:
		if ltx:
			for section in ltx.iter_sections():
				yield section
			for ltx in ltx.ltxs:
				for section in ltx.iter_sections():
					yield section

	def load_maps(self) -> tuple[str] | None:
		'return maps names'
		self.maps = self.global_map = None
		maps_names = None
		maps: list[Ltx.Section] = []
		# load global map and maps names sections
		for section in self.iter_sections(Ltx(self.paths.game_ltx)):
			match section.name:
				case 'level_maps_single':
					maps_names = tuple(map(str.lower, section.iter_names()))
				case 'global_map':
					self.global_map = section
			if maps_names and self.global_map:
				break
		# load maps sections
		if maps_names:
			for section in self.iter_sections(Ltx(self.paths.game_ltx)):
				if section.name.lower() in maps_names:
					maps.append(section)
					if len(maps) == len(maps_names):
						break  # all maps sections loaded
		if maps:
			self.maps = tuple(maps)

	def get_image(self, section: Ltx.Section) -> Image:
		if section and (texture := section.get('texture')):
			return image_open(self.paths.join(self.paths.gamedata, 'textures', texture+'.dds'))


if __name__ == '__main__':
	from sys import argv
	import argparse

	DEFAULT_IMAGE_EXT = '.png'

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='game.ltx parser',
				epilog=f'Examples: {argv[0]} -f Stalker/gamedata',
			)
			parser.add_argument('-f', metavar='PATH', help='gamedata path')
			parser.add_argument('-i', action='store_true', help='save map images to .png files')
			return parser.parse_args()

		# read command line arguments
		args = parse_args()

		maps = Maps(args.f)
		# print maps names
		if maps.maps:
			for section in maps.maps:
				print(f'{section.name}')
		# save maps images
		if (image := maps.get_image(maps.global_map)):  # get map image
			# save image
			image_path = f'global_map{DEFAULT_IMAGE_EXT}'
			print(f'Save image: {image_path}')
			image.save(image_path)
		else:
			print(f'Image error: global_map{DEFAULT_IMAGE_EXT}')
		if args.i and maps.maps:
			for section in maps.maps:
				if (image := maps.get_image(section)):  # get map image
					# save image
					image_path = section.name + DEFAULT_IMAGE_EXT
					print(f'Save image: {image_path}')
					image.save(image_path)
				else:
					print(f'Image error: {section.name}')

	main()
