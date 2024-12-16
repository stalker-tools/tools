#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker tools and Odyssey main game tools
# Author: Stalker tools, 2023-2024

# It has simple interface with Xray - periodic poll for changed .sav files
# Odyssey web interface has one profile: radio audio
# Note. It multithreaded and has threads:
# - web
# - timer to run _update_savings method

from typing import Callable, Iterator
from dataclasses import dataclass
from sys import exit, path
from time import sleep, monotonic
from os.path import getctime
from pathlib import Path
from io import BytesIO
from email.utils import formatdate, parsedate_tz, mktime_tz
from threading import Thread, Lock
from bottle import route, view, run, static_file, response, request
import qrcode
from PIL.Image import open as image_open, Image
from PIL.ImageDraw import Draw
# tools imports
web_module_path = Path(__file__).parent.absolute()
path.append(str(web_module_path.parent.absolute()))  # add tools modules path
from Game import Game, DEFAULT_FSGAME_FILE_NAME, DEFAULT_ODYSSEY_CONFIG_FILE_NAME
from ltx_tool import Ltx
from Odyssey import Odyssey, MapChanged


DEFAULT_PROFILES = 'profiles'  # web devices profile with .htm files
BROCHURE_FILE_NAME = 'Brochure.html'
DEFAULT_SERVER_IP = '0.0.0.0'
DEFAULT_SERVER_PORT = 8080
DEFAULT_BLACK_STYLE = True
DEFAULT_IMG_FORMAT = 'webp'  # MIME image type (see https://developer.mozilla.org/en-US/docs/Web/HTTP/MIME_types)
DEFAULT_SAVED_GAMES_CACHE_REFRESH_TIME = 5  # seconds
TEMPLATES_LOOKUP = (str(web_module_path),)  # .tpl files paths

def map_name_convert(map_name: str) -> str:
	'converts game.graph level name to simple map name'
	return map_name.partition('_')[2]


class WebOdyssey(Odyssey):
	'Odyssey game for web'

	@property
	def profiles_static_path(self) -> Path:
		return self.game.config.odyssey_path.joinpath('profiles').joinpath('static')

	def set_radio_audio(self, file_path: str):
		self.game.set_radio_audio(self.profiles_static_path.joinpath(file_path))


class WebGame(Game):
	'Xray and Odyssey game: web interface'

	# Xray map changed event: .sav files poll engine classes


	class MapsNotFoundError(Exception): pass


	class PeriodicTimer:
		'periodically runs callback on separate thread'

		def __init__(self, callback: Callable, time_delta: int):
			self.callback, self.time_delta = callback, int(time_delta)
			if self.time_delta == 0:
				raise ValueError(f'time_delta must be int and > 0: {self.time_delta}')
			self._stop, self._remain = False, 0
			self.thread = Thread(target=self._run)

		def start(self):
			self._stop = False
			self.thread.start()

		def _run(self):
			while not self._stop:
				if self._remain > 0:
					self._remain -= 1
					sleep(1.0)
					continue
				self._remain = self.time_delta
				# timer tick
				self.callback(self)
				# print(f'{monotonic():0.6f} !!! timer tick: sleep {self.time_delta} s')

		def stop(self):
			self._stop = True
			self.thread.join()


	@dataclass
	class GameSave:
		'game save .sav file cache'
		name: str  # .sav file name stem (see Path)
		file_path: str  # .sav path
		file_time: float  # .sav file time
		map_name: str  # map (level) name
		map_name_localized: str  # map localized name
		health: float  # actor health
		position: tuple[float, float, float] | None  # actor position


	# Odyssey event data classes


	@dataclass
	class WebMapChanged(MapChanged):
		gs: 'WebGame.GameSave'
		def iter_actor_objects(self, actor_only=False) -> Iterator[dict]:
			yield from game.iter_save_actor_objects(self.gs.file_path, actor_only)
		def has_actor_object(self, name: str) -> bool:
			return game.has_save_actor_object(self.gs.file_path, name)


	# Web Game methods

	def __init__(self, config: Game.Config) -> None:
		super().__init__(config)
		self.config = config  # load stalker and stalker-tools configs
		# check config
		if any(map(lambda x: not x, (self.config.maps, self.config.maps.maps, self.config.maps.global_map))):
			raise self.MapsNotFoundError()
		self.global_map_name = self.config.maps.global_map.name
		# load game savings .sav files
		self._savings_cache: tuple['GameSave'] = tuple()
		self._savings_cache_timer = self.PeriodicTimer(self._update_savings, DEFAULT_SAVED_GAMES_CACHE_REFRESH_TIME)
		self._savings_cache_timer.lock = Lock()  # savings cache lock
		self._savings_cache_timer.inited = False  # is a savings change detection inited
		self._savings_cache_timer.has_all = False  # has all.sav file
		self.is_black_style = DEFAULT_BLACK_STYLE
		# profiles
		self.profiles = self.config.odyssey.get('web', 'profiles', fallback=None) or DEFAULT_PROFILES
		self.radio_audio: Path | None = None
		# Odyssey game
		self.odyssey = WebOdyssey(self)
		path.append(str(self.config.odyssey_python_root_file_path.parent.absolute()))
		self.odyssey_root =  __import__(self.config.odyssey_python_root_file_path.stem)

	@property
	def savings(self) -> tuple[GameSave]:
		with self._savings_cache_timer.lock:
			return self._savings_cache

	def _update_savings(self, timer: PeriodicTimer):
		'''updates game savings cache
		Used to Xray .sav files and Odyssey synchronize
		Note: this method run into separate thread'''

		def get_level_from_actor_client_data(client_data: bytes) -> tuple[str, str] | None:
			'returns map name and localized name from lua pstore'
			if not client_data or not self.config.maps:
				return None
			for map_name in self.config.iter_map_names():
				if client_data.find(map_name.encode()+b'\0') > 0:
					# map name found # localize it
					return map_name, self.localize(map_name)
			return None

		def get_level_from_graph_vertex(id: int | None) -> tuple[str, str] | None:
			'returns map name and localized name from graph vertex id'
			if (map_name := self.get_map_name_by_graph(id)):
				return map_name, self.localize(map_name)
			return None

		def get_cached_file(file_path: str) -> 'GameSave | None':
			for sc in self._savings_cache:
				if sc.file_path == file_path:
					return sc
			return None

		def print_files(files: 'tuple[GameSave]', title: str):
			if files:
				max_name = max((len(x.name) for x in files))
				print(f'{title} .SAV FILES:')
				for i, sv in enumerate(files):
					print(f'\t{i:02}\t{sv.name:{max_name}}\t{sv.map_name_localized}\t{sv.file_time}')
			else:
				print(f'{title} .SAV FILES: <NONE>')

		def remove_files(files: 'tuple[GameSave]', title: str):
			if files:
				print_files(files, title)
				buff = list(self._savings_cache)
				for gs in files:
					buff.remove(gs)
				self._savings_cache = tuple(buff)

		add_files = changed_files = None
		has_all = False
		# print(f'B {timer.inited=} {timer.has_all=}')
		with timer.lock:
			removed_files = list(self._savings_cache)
			for sav_file in self.savings_path.glob('*.sav'):  # find .sav files
				if sav_file.stem.lower() == 'all':
					has_all = True
				else:
					abs_path = sav_file.absolute()
					file_time = getctime(abs_path)
					if (cached_file := get_cached_file(abs_path)):
						removed_files.remove(cached_file)
						if cached_file.file_time == file_time:
							continue  # file not changed
						# file was updated
						if not changed_files:
							changed_files = []
						changed_files.append(cached_file)
					# there is file that missing in cache
					if not add_files:
						add_files = []
					for data in self.iter_save_actor_objects(abs_path):  # parse .sav file and iterate actor objects
						if data.get('id') == 0:
							add_files.append(self.GameSave(sav_file.stem, abs_path, file_time,
								# *get_level_from_actor_client_data(data.get('client_data')) or ('', ''),
								*get_level_from_graph_vertex(data.get('graph_id')) or ('', ''),
								data.get('health', 1.0), data.get('position')))
							break
			remove_files(changed_files, 'CHANGE')
			if add_files:
				print_files(add_files, 'ADD')
				add_files.extend(self._savings_cache)
				self._savings_cache = tuple(sorted(add_files, key=lambda x: x.file_time))
			remove_files(removed_files, 'REMOVE')
		if has_all != timer.has_all:
			timer.has_all = has_all
			if timer.inited:
				self._has_all_changed(has_all)
		if add_files or changed_files or removed_files:
			print_files(self._savings_cache, 'NEW')
			if timer.inited:
				self._savings_changing(add_files, changed_files, removed_files)
		timer.inited = True
		# print(f'A {timer.inited=} {timer.has_all=}')

	def _savings_changing(self, add: tuple[GameSave], changed: tuple[GameSave], removed: tuple[GameSave]):
		'Xray .sav files changed'
		if add or changed:
			# map enter
			if (gs := next((x for x in add or changed if x.name.endswith('_autosave')), None)):
				map_name = map_name_convert(gs.map_name)
				# check is first enter to map
				if any((x for x in self.savings if x.map_name == gs.map_name and x != gs)):
					# no, there is another savings with the same map
					self.odyssey.map_changed(self.WebMapChanged(map_name, False, gs))
					return
				# it first enter to map
				self.odyssey.map_changed(self.WebMapChanged(map_name, True, gs))

	def _has_all_changed(self, has_all: bool):
		'Xray all.sav file changed'
		print(f'!!! HAS ALL changed: {has_all}')

	# media profile

	def get_media_file_mime(self, file_path: Path) -> str | None:
		'''returns mime type for media file
		See https://developer.mozilla.org/ru/docs/Web/HTTP/MIME_types
		'''
		# check file
		if not file_path.exists():
			print(f'Media file not exists: {file_path}')
			return None
		# check audio file
		match file_path.suffix.lower():
			case '.mp3':
				return 'audio/mpeg'
			case '.ogg':
				return 'audio/ogg'
			case _:
				print(f'Nedia type not supported: {file_path}')
				return None

	def set_radio_audio(self, file_path: Path):
		if self.get_media_file_mime(file_path):
			self.radio_audio = file_path
		else:
			print(f'Audio for radio profile file not correct: {file_path}')


@dataclass
class ActorObject:
	'.sav file object that belongs to actor. Used as cache to render web interface'
	object: dict[str, str]  # .sav file object
	section: Ltx.Section  # game .ltx file section of object
	quantity: int = 0  # .sav file object quantity (if any)
	def localize(self) -> str:
		if (inv_name_short := self.section.get('inv_name_short')):
			return game.localize(inv_name_short, True)
		elif (inv_name := self.section.get('inv_name')):
			return game.localize(inv_name, True)
		return ''


game: WebGame

# web server API

@route('/')
@view('root.tpl', template_lookup=TEMPLATES_LOOKUP)
def root():
	return {'game': game}

@route('/brochure')
def brochure():
	return static_file(BROCHURE_FILE_NAME, game.config.game_path)

@route('/savings')
@view('savings.tpl', template_lookup=TEMPLATES_LOOKUP)
def savings():
	return {'game': game, 'savings': game.savings}

@route('/save/<id>')
@view('save.tpl', template_lookup=TEMPLATES_LOOKUP)
def save(id: str):
	# find cached .sav and render it
	for gs in game.savings:
		if gs.name == id:
			return {'game': game, 'id': id, 'gs': gs, 'iter_actor_objects': iter_actor_objects}
	response.status = 404
	return None

@route('/itemimg/<id>')
def itemimg(id: str):
	'id: section'
	if (section := game.get_section(id)):
		inv_grid = (int(section.get('inv_grid_x')), int(section.get('inv_grid_y')), int(section.get('inv_grid_width', 1)), int(section.get('inv_grid_height', 1)))
		return send_img(game.config.icons.get_image(*inv_grid), 1)
	response.status = 404
	return None

@route('/saveimg/<id>')
def saveimg(id: str):
	'id: .sav file name'
	if (p := Path(game.savings_path).joinpath(f'{id}.dds')) and p.exists():
		return send_img_from_file(p.absolute())
	response.status = 404
	return None

@route('/mapimg/<id>')
def mapimg(id: str):
	'id: .sav file name stem or global map name'
	if id == game.global_map_name:
		# global map
		if (section := game.config.maps.get_map_section(id)):
			return send_img_from_file(game.config.maps.get_image_file_path(section), 1)
	elif (gs := get_save(id)) and (section := game.config.maps.get_map_section(gs.map_name)):  # get map from save
		# map with actor point from save
		return send_img_from_file(game.config.maps.get_image_file_path(section), 1, gs)
	response.status = 404
	return None

# Brython files

@route('/brython.js')
@route('/brython_stdlib.js')
def brython():
	return static_file(request.path[1:], web_module_path)

# Odyssey Profile API

@route('/profiles/<id>')
def profiles(id: str):
	return static_file(f'{id}.htm', game.config.odyssey_path.joinpath(game.profiles))

@route('/profiles/static/<id>')
def profiles_static(id: str):
	return static_file(id, game.config.odyssey_path.joinpath(game.profiles, 'static'))

@route('/profiles/audio')
def profiles_audio():
	if (file_path := game.radio_audio):
		# set mime type
		if (mime := game.get_media_file_mime(file_path)):
			response.headers['Content-Type'] = mime
			game.radio_audio = None  # send only once
			# send audio file
			with open(file_path, 'rb') as f:
				return f.read()
	response.status = 404
	return None

@route('/api')
def api():
	response.headers['Content-Type'] = 'application/xml'
	ret = '<odyssey>'
	if game.radio_audio:
		ret += f'<audio href="/profiles/static/{game.radio_audio.name if game.radio_audio else ''}"/>'
	ret += '</odyssey>'
	return ret

# web game API

def get_save(save_name: str) -> WebGame.GameSave | None:
	'returns cached game save by .sav file name stem'
	for gs in game.savings:
		if gs.name == save_name:
			return gs

def send_img_from_file(image_file_path: str, default_reduce = 2, gs: WebGame.GameSave | None = None):
	'sends image with client side cache ability: HTTP 304'
	if image_file_path:
		if (image_file_ctime := int(getctime(image_file_path) or None)):
			response.headers['Last-Modified'] = formatdate(image_file_ctime, usegmt=True)
		if (if_modified_since := request.headers.get('If-Modified-Since')):
			if image_file_ctime == mktime_tz(parsedate_tz(if_modified_since)):
				response.status = 304
				return None
		image = image_open(image_file_path)
		if gs:
			# add actor position from save
			mark_map_position(gs, image)
		return send_img(image, default_reduce)
	response.status = 404
	return None

def iter_actor_objects(gs: WebGame.GameSave | None) -> Iterator[ActorObject]:
	'iterate actor object from .sav file with sorting by .ltx class'
	if gs:
		objects: dict[str, ActorObject] = {}  # because quantity need to be aggregated
		# aggregate the object quantity with the same .ltx section
		for object in game.iter_save_actor_objects(gs.file_path):
			if (name := object.get('name')):
				if name in objects:
					objects[name].quantity += object.get('elapsed', 1)
				else:
					objects[name] = ActorObject(object, game.get_section(object.get('name')), object.get('elapsed', 1))
		# at last sort objects by .ltx class and yield
		for object in sorted(objects.values(), key=lambda x: x.section.get('class') if x.section else ''):
			yield object

def mark_map_position(gs: WebGame.GameSave, img: Image) -> Image:
	'modifies map image: add marked point from save'
	POINT_SIZE, POINT_COLOR, POINT_COLOR2 = 14, 'red', 'yellow'
	pos = gs.position
	if pos and len(pos) == 3 and img and (section := game.config.maps.get_map_section(gs.map_name)):  # check args
		if (bound_rect := section.get('bound_rect')) and len(bound_rect) == 4:  # get map rect
			# calc map to image scale
			bound_rect = tuple(map(float, bound_rect))
			x_scale = img.width / (bound_rect[2] - bound_rect[0])
			y_scale = img.height / (bound_rect[3] - bound_rect[1])
			# calc actor mark as map image coords
			x, y = (pos[0] - bound_rect[0]) * x_scale, img.height - (pos[2] - bound_rect[1]) * y_scale
			# place actor mark to map image
			draw = Draw(img)
			draw.ellipse((x - POINT_SIZE / 2, y - POINT_SIZE / 2, x + POINT_SIZE, y + POINT_SIZE),
				POINT_COLOR, POINT_COLOR2)

def get_img_reduce(default_reduce = 2):
	'default_reduce: image resize koef.'
	try:
		if (s := float(request.query.get('s'))) and 0 < s < 10:
			return s
	except: pass
	return default_reduce

def send_img(image: Image, default_reduce = 2):
	'default_reduce: image resize koef.'
	buff = BytesIO()
	reduce = get_img_reduce(default_reduce)
	image = image.resize(tuple(map(lambda x: int(x * reduce), image.size)))
	image.save(buff, format=DEFAULT_IMG_FORMAT)
	buff.seek(0)
	response.content_type = f'image/{DEFAULT_IMG_FORMAT}'
	return buff.read()

# command line API

if __name__ == '__main__':
	from sys import argv
	import argparse

	def main():
		global game

		def parse_args():
			parser = argparse.ArgumentParser(
				description='Game web server',
				epilog=f'Examples: {argv[0]} -g ~/.wine/drive_c/Program Files (x86)/GSC World Publishing/S.T.A.L.K.E.R',
			)
			parser.add_argument('-g', '--game', metavar='PATH', required=True, help='Game path; example: S.T.A.L.K.E.R')
			parser.add_argument('--fsgame', metavar='PATH', default=DEFAULT_FSGAME_FILE_NAME, help=f'fsgame.ltx file path; default: {DEFAULT_FSGAME_FILE_NAME}')
			parser.add_argument('-a', '--address', metavar='IP', default=DEFAULT_SERVER_IP, help=f'IP address; example: 192.168.0.18; default: {'all network interfaces' if DEFAULT_SERVER_IP == '0.0.0.0' else DEFAULT_SERVER_IP}')
			parser.add_argument('-p', '--port', metavar='IP', default=DEFAULT_SERVER_PORT, help=f'Tcp port; example: 8080; default: {DEFAULT_SERVER_PORT}')
			parser.add_argument('-s', '--settings', metavar='PATH', default=DEFAULT_ODYSSEY_CONFIG_FILE_NAME, help=f'Odyssey config file path; default: {DEFAULT_ODYSSEY_CONFIG_FILE_NAME}')
			parser.add_argument('-d', '--debug', action='store_true', help='Enable debug')
			return parser.parse_args()

		# read command line arguments
		args = parse_args()

		try:
			config = WebGame.Config(args.game, fsgame_file_name=args.fsgame)
		except (WebGame.GamePathNotExistsError, WebGame.GamePathNotValidError):
			exit(-1)
		except WebGame.FsgameFileNotFoundError:
			exit(-2)
		except (WebGame.GamedataPathNotExistsError, WebGame.GamedataPathNotValidError):
			exit(-3)

		game = WebGame(config)
		if args.debug:
			print('Cache savings')
		game._savings_cache_timer.start()

		# show QR code to mobile client to open web page
		if args.address != '0.0.0.0':  # is IP address defined
			qr = qrcode.QRCode()
			qr.add_data(f'http://{args.address}:{args.port}/')
			qr.print_ascii()

		# run web server
		# run(host=args.address, port=args.port, reloader=args.debug, debug=args.debug)
		t = Thread(target=run, kwargs=dict(host=args.address, port=args.port, reloader=False, debug=args.debug))
		t.run()
		if args.debug:
			print('\tWaiting while all threads stopped')
		try:
			game._savings_cache_timer.stop()
		except KeyboardInterrupt: pass

	main()
