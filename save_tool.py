#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker Xray game .sav file tool
# Author: Stalker tools, 2023-2024

from typing import Iterator, Callable
from enum import Enum
import lzo
# tools imports
from ChunkReader import ChunkReader
from SequensorReader import SequensorReader, OutOfBoundException


class Save:
	'reads .sav files'


	class ChunkTypes(Enum):
		ALIFE = 0x0000
		SPAWN = 0x0001
		OBJECT = 0x0002
		GAME_TIME = 0x0005
		REGISTRY = 0x0009
		SCRIPT_VARS = 0x000D


	class Chunk(ChunkReader):
		'base chunk'
		def __init__(self, type: int, parent_pos: int, buff: bytes) -> None:
			ChunkReader.__init__(self, buff)
			self.type, self.size, self.parent_pos = Save.ChunkTypes(type), len(buff), parent_pos
		def __str__(self) -> str:
			return f'Chunk type={self.type} size={self.size}'
		def iter_data(self) -> Iterator[dict[str, str]]:
			pass


	class AlifeChunk(Chunk):

		def iter_data(self) -> Iterator[dict[str, str]]:
			if self.size == 4 and (version := self.sr.read('I')) and version >= 2:
				yield {'version': version}


	class GameTimeChunk(Chunk):

		def iter_data(self) -> Iterator[dict[str, str]]:
			if self.size == 16:
				yield dict(zip(('time_id', 'time_factor', 'normal_time_factor'), self.sr.read('Qff')))


	class SpawnChunk(Chunk):
		'chunk contains subchunks'

		def iter_data(self) -> Iterator[dict[str, str]]:
			# iterate subchunks
			# CALifeSpawnRegistry::load
			for type, _, bytes in self.iter():
				match type:
					case 0:
						sr = SequensorReader(bytes)
						yield dict(zip(('subchunk_type', 'spawn_name', 'GUID'), (0, sr.read_string(), sr.read_bytes(16))))
					case 1:
						# spawn graph vertices
						sr = SequensorReader(bytes)
						yield dict(zip(('subchunk_type', 'vertex_id',), (1, sr.read('I'))))


	class ObjectChunk(Chunk):
		'chunk contains subchunks'

		def iter_data(self) -> Iterator[dict[str, str]]:
			# iterate subchunks: each subchunk contains spawn and update net packets
			# CALifeObjectRegistry::load
			count = self.sr.read('I')  # subchunks count
			for i in range(count):
				data = {}
				# read spawn net packet
				# CALifeObjectRegistry::get_object
				# spawn
				net_packet_len_s = self.sr.read('H')
				sr = SequensorReader(self.sr.read_bytes(net_packet_len_s))
				id_s, name_s = sr.read('H'), sr.read_string()  # M_SPAWN=1, section name
				# F_entity_Create(name_s)
				# CSE_Abstract::Spawn_Read
				# generic
				data['name'] = name_s
				data['name_replace'] = sr.read_string()
				data['game_id'], data['rp'] = sr.read('BB')
				data['position'] = sr.read('fff')
				data['angle'] = sr.read('fff')
				data.update(dict(zip(('respawn_time', 'id', 'id_parent', 'id_phantom', 'flags'), sr.read('HHHHH'))))
				if data['flags'] & 0b10_0000:  # M_SPAWN_VERSION
					version = sr.read('H')
					data['version'] = version
					if not version:
						yield data
						continue
					if version > 69:
						data['script_version'] = sr.read('H')
					# read specific data
					if version > 70:
						if (client_data_size := sr.read('H') if version > 93 else sr.read('B')):
							data['client_data'] = sr.read_bytes(client_data_size)
					if version > 79:
						data['spawn_id'] = sr.read('H')
					# if version < 112:
					# 	if version > 82:
					# 		sr.read('f')
					# 	if version > 83:
					# 		sr.read('I')
					# 		sr.read_string()
					# 		sr.read('IIQ')
					# 	if version > 84:
					# 		sr.read('QQ')
					size = sr.read('H')
					# STATE_Read


					if name_s == 'actor':
						# CSE_ALifeCreatureActor::STATE_Read
						# CSE_ALifeCreatureAbstract::STATE_Read
						# CSE_ALifeDynamicObjectVisual::STATE_Read
						# CSE_ALifeDynamicObject::STATE_Read
						# CSE_ALifeObject::STATE_Read
						if version >= 1:
							if version > 24:
								if version < 83:
									sr.read('f')  # m_spawn_probability
							else:
								sr.read('B')  # m_spawn_probability
							if version < 83:
								sr.read('I')
							if version < 4:
								sr.read('H')
							data['graph_id'], data['distance'] = sr.read('Hf')
						if version >= 4:
							sr.read('I')  # is direct control
						if version >= 8:
							data['node_id'] = sr.read('I')
						if version > 22 and version <= 79:
							data['spawn_id'] = sr.read('H')
						if version > 23 and version < 84:
							data['spawn_control'] = sr.read_string()
						if version > 49:
							sr.read('I')
						if version > 57:
							data['ini_string'] = sr.read_string()
						if version > 61:
							data['story_id'] = sr.read('I')
						if version > 111:
							data['spawn_story_id'] = sr.read('I')

						# CSE_ALifeDynamicObjectVisual::STATE_Read
						if version > 31:
							# CSE_Visual::visual_read
							data['visual_name'] = sr.read_string()  # visual name
							if version > 103:
								sr.read('B')  # flags

						# CSE_ALifeCreatureAbstract::STATE_Read
						data.update(dict(zip(('team', 'squad', 'group'), sr.read('BBB'))))

						if version > 18:
							data['health'] = sr.read('f')
						if version < 115:
							data['health'] /= 100.0

						# if version > 87:
						# 	load_data m_dynamic_out_restrictions xr_vector<u16>
						# 	load_data m_dynamic_in_restrictions  xr_vector<u16>

						# if version > 94:
						# 	killer_id = sr.read('H')

						# if version > 115:
						# 	game_death_time = sr.read('Q')

						# CSE_ALifeTraderAbstract::STATE_Read
						# if version < 108:
						# 	sr.read('I')

						# if version > 62:
						# 	money = sr.read('I')

						# if version > 75 and version < 98:
						# 	sr.read('i')  # CSpecificCharacter::IndexToId
						# elif version >= 98:
						# 	specific_character = sr.read_string()

						# if version > 77:
						# 	trader_flags = sr.read('I')

						# if version > 81 and version < 96:
						# 	sr.read('i')  # CCharacterInfo::IndexToId
						# elif version > 95:
						# 	character_profile = sr.read_string()

						# if version > 85:
						# 	community_index = sr.read('i')

						# if version > 86:
						# 	rank, reputation = sr.read('ii')

						# if version > 104:
						# 	character_name

						# # CSE_ALifeCreatureActor::STATE_Read
						# if version > 91:
						#	# CSE_PHSkeleton::STATE_Read
						#	startup_animation = sr.read_string()
						#	flags, source_id = sr.read('BH')
						#	if flags & (1 << 2):  # flSavedData
						#		# SPHBonesData::net_Load
						# 		bones_mask, root_bone = sr.read('QH')
						# 		sr.read('fff')
						# 		sr.read('fff')
						# 		bones_number = sr.read('H')
						# 		for i in range(bones_number):
						# 			sr.read('BBB')  # quaternion, quaternion, enabled
						# if version > 88:
						# 	holder_ID = sr.read('H')

					# CSE_ALifeItem::STATE_Read
					# if ((m_tClassID == CLSID_OBJECT_W_BINOCULAR) && (m_wVersion < 37)) {
					# 	tNetPacket.r_u16		();
					# 	tNetPacket.r_u16		();
					# 	tNetPacket.r_u8			();
					# }
					# CSE_ALifeInventoryItem::STATE_Read
					# if version > 52:
					# 	condition = sr.read('f')
				# read update net packet
				net_packet_len_u = self.sr.read('H')
				sr = SequensorReader(self.sr.read_bytes(net_packet_len_u))
				id_u = sr.read('H')#, sr.read_bytes()  # M_UPDATE=0, buffer
				# id_u, buff_u = sr.read('H')#, sr.read_bytes()  # M_UPDATE=0, buffer
				# print(f'\t\tnet_packet {i:05} len={net_packet_len_s:05}/{net_packet_len_u:05} name={name_s:^15} repl={name_replace:^19} {game_id=} {rp=} pos=({','.join(f'{x:.0f}' for x in position)}) angle=({','.join(f'{x:.0f}' for x in angle)}) {respawn_time=} {id=} {version=} {flags=:b}{f' id_parent={id_parent}' if id_parent != 0xffff else ''}{f' id_phantom={id_phantom}' if id_phantom != 0xffff else ''}')
				# print(buff_u.hex())
				# print(buff_u.decode('windows-1251', errors='replace').replace('\n', '').replace('\r', ''))
				if (update := Objects.get_update(name_s)):
					data.update(update(sr, version))
				yield data


	def __init__(self, file_path: str) -> None:
		self.file_path = file_path
		self.sr = self._read_save_file()

	def _read_save_file(self) -> SequensorReader:
		'read and decompress .sav file'
		with open(self.file_path, 'rb') as f:
			# read magic & version
			sr = SequensorReader(f.read())
			magic, version = sr.read('II')
			if magic != 0xffffffff:
				return None
			if version < 2:
				return None
			unpacked_len = sr.read('I')
			# print(f'{magic=:X} {version=} {unpacked_len=}')
			# decompress without lzo header and use decompressed buffer as chunks
			return SequensorReader(lzo.decompress(sr.read_bytes(), False, unpacked_len, algorithm='LZO1X'))

	def iter_chunks(self) -> Iterator[Chunk]:
		if self.sr:
			self.sr.pos = 0
			while self.sr.pos < len(self.sr.buff):
				type, size = self.sr.read('II')
				pos = self.sr.pos
				buff = self.sr.read_bytes(size)
				# print(f'{type=}, {size=}')
				match type:
					case self.ChunkTypes.ALIFE.value:
						chunk = self.AlifeChunk(type, pos, buff)
						yield chunk
					case self.ChunkTypes.GAME_TIME.value:
						chunk = self.GameTimeChunk(type, pos, buff)
						yield chunk
					case self.ChunkTypes.SPAWN.value:
						chunk = self.SpawnChunk(type, pos, buff)
						yield chunk
					case self.ChunkTypes.OBJECT.value:
						chunk = self.ObjectChunk(type, pos, buff)
						yield chunk
					case self.ChunkTypes.REGISTRY.value:
						pass
					case self.ChunkTypes.SCRIPT_VARS.value:
						pass


class Objects:

	def get_update(name: str) -> Callable | None:
		for k, v in Objects.NAMES.items():
			for _name in v:
				if _name.endswith('*'):
					if name.startswith(_name[:-1]):
						return k
				elif name == _name:
					return k
		return None

	class Update:

		@classmethod
		def CSE_ALifeCreatureActor(cls, sr: SequensorReader, version: int) -> dict:
			# for version >= 21
			ret = cls.CSE_ALifeCreatureAbstract(sr, version)
			ret['mstate'] = sr.read('H')
			ret['accel'] = sr.read('Hf')
			ret['velocity'] = sr.read('Hf')
			ret['radiation'] = sr.read('f')
			ret['weapon'] = sr.read('B')
			ret['num_items'] = sr.read('H')
			if ret['num_items'] == 1:
				sr.read('Bfffffffffffffffffff')
			return ret

		@classmethod
		def CSE_ALifeCreatureAbstract(cls, sr: SequensorReader, version: int) -> dict:
			ret = {}
			ret['health'], ret['timestamp'], ret['flags'] = sr.read('fIB')
			ret['position'] = sr.read('fff')
			ret['model'], ret['yaw'], ret['pitch'], ret['roll'], ret['team'], ret['squad'], ret['group'] = sr.read('ffffBBB')
			return ret

		@classmethod
		def CSE_ALifeItemAmmo(cls, sr: SequensorReader, version: int) -> dict:
			# CSE_ALifeItemAmmo::UPDATE_Read
			ret = cls.CSE_ALifeInventoryItem(sr, version)
			ret['elapsed'] = sr.read('H')
			return ret

		@classmethod
		def CSE_ALifeInventoryItem(cls, sr: SequensorReader, version: int) -> dict:
			# CSE_ALifeInventoryItem::UPDATE_Read
			ret = {}
			ret['num_items'] = sr.read('B')
			if ret['num_items']:
				# print(f'num_items={bin(ret['num_items'])}', sr.read_bytes(update_position=False).hex())
				ret['num_items'], mask = ret['num_items'] & 0b1_1111, (ret['num_items'] >> 5) & 0b111
				sr.read('fff')  # position
				sr.read('BBBB')  # quaternion
				if not (mask & 0b010):  # inventory_item_angular_null
					sr.read('BBB')  # angular_vel
				if not (mask & 0b100):  # inventory_item_linear_null
					sr.read('BBB')  # linear_vel
			return ret


Objects.NAMES = {
	Objects.Update.CSE_ALifeCreatureActor: ('actor',),
	# Objects.Update.CSE_ALifeItem: ('obj_medkit', 'obj_bandage', 'obj_antirad', 'obj_food', 'obj_bottle'),
	# Objects.Update.CSE_ALifeItemExplosive: ('obj_explosive',),
	# Objects.Update.CSE_ALifeItemCustomOutfit: ('equ_scientific', 'equ_stalker', 'equ_military', 'equ_exo', 'equ_stalker_s'),
	# Objects.Update.CSE_ALifeItemGrenade: ('wpn_grenade_f1', 'wpn_grenade_rgd5'),
	# Objects.Update.CSE_ALifeItemWeaponMagazinedWGL: ('wpn_ak74_s', 'wpn_groza_s', 'wpn_wmaggl', 'wpn_fn2000', 'wpn_ak74', 'wpn_groza'),
	# Objects.Update.CSE_ALifeItemWeaponMagazined: ('wpn_lr300_s', 'wpn_binocular_s', 'wpn_svd_s', 'wpn_hpsa_s', 'wpn_pm_s', 'wpn_rpg7_s', 'wpn_svu_s', 'wpn_usp45_s', 'wpn_val_s', 'wpn_vintorez_s', 'wpn_walther_s',
	# 	'wpn_wmagaz', 'wpn_lr300', 'wpn_hpsa', 'wpn_pm', 'wpn_fort', 'wpn_binocular', 'wpn_svd', 'wpn_svu', 'wpn_rpg7', 'wpn_val', 'wpn_vintorez', 'wpn_walther', 'wpn_usp45'),
	# Objects.Update.CSE_ALifeItemWeaponShotGun: ('wpn_shotgun', 'wpn_bm16', 'wpn_rg6', 'wpn_bm16_s', 'wpn_rg6_s', 'wpn_shotgun_s'),
	Objects.Update.CSE_ALifeItemAmmo: ('wpn_ammo', 'wpn_ammo_vog25', 'wpn_ammo_og7b', 'wpn_ammo_m209', 'ammo*'),
	# Objects.Update.CSE_ALifeMonsterBase: ('flesh', 'chimera', 'dog_red', 'bloodsucker', 'boar', 'dog_black', 'psy_dog', 'burer', 'pseudo_gigant', 'controller', 'poltergeist', 'zombie', 'fracture', 'snork', 'cat', 'tushkano'),
	# Objects.Update.CSE_ALifeHumanStalker: ('stalker',),
	# Objects.Update.CSE_ALifePsyDogPhantom: ('psy_dog_phantom',),
	# Objects.Update.CSE_ALifeItemArtefact: ('art_mercury_ball' , 'art_black_drops' , 'art_needles' , 'art_bast_artefact' , 'art_gravi_black' , 'art_dummy' , 'art_zuda' , 'art_thorn' , 'art_faded_ball' , 'art_electric_ball' , 'art_rusty_hair' , 'art_galantine' , 'art_gravi' , 'artefact', 'artefact_s'),
	}


if __name__ == '__main__':
	from sys import argv, stderr
	import argparse

	def main():
		global game_path, title

		def parse_args():
			parser = argparse.ArgumentParser(
				description='Game web server',
				epilog=f'Examples: {argv[0]} -f savedgames/all.sav',
			)
			parser.add_argument('-f', metavar='PATH', required=True, help='Game save .sav file path; example: savedgames/all.sav')
			parser.add_argument('--client-data', action='store_true', help='binary dump of client_data of actor')
			parser.add_argument('--map', action='store_true', help='show top-level chunks offset and size')
			return parser.parse_args()

		# read command line arguments
		args = parse_args()

		save = Save(args.f)
		for chunk in save.iter_chunks():
			if args.map:
				print(f'Chunk: offset={chunk.parent_pos}, length={chunk.size}')
			for data in chunk.iter_data():
				if not args.client_data:
					print(type(chunk).__name__, data)
				elif chunk.type == Save.ChunkTypes.OBJECT and data.get('id') == 0:
					# binary dump of actor client_data
					from sys import exit, stdout
					stdout.buffer.write(data.get('client_data', b''))
					exit()
				# if type(chunk) is Save.ObjectChunk and (client_data := data.get('client_data')):
				# 	print(f'\tclient_data={client_data.hex()}')
				# 	print('\tclient_data=', end='')
				# 	for byte in client_data:
				# 		print(f'{chr(byte)} ' if 32 < byte < 127 else '  ', end='')
				# 	print()

	try:
		main()
	except FileNotFoundError as e:
		print(e, file=stderr)
