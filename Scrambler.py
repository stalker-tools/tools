
# Xray .db files reader
# Author: Stalker tools, 2023-2025

from enum import IntEnum


class XRScramblerConfig(IntEnum):
	CC_RU = 1
	CC_WW = 2


class UnknownConfig(Exception): pass


# def write_to_file(file_name: str, buff: bytes):
# 	# for debug purposes
# 	print(f'\twrite to file: {file_name}')
# 	with open(file_name, 'wb') as f:
# 		f.write(buff)

class XRScrambler:
	# Constants
	SEED_MULT = 0x8088405
	SEED_RU = 0x131a9d3
	SEED0_RU = 0x1329436
	SIZE_MULT_RU = 8
	SEED_WW = 0x16eb2eb
	SEED0_WW = 0x5bbc4b
	SIZE_MULT_WW = 4
	SBOX_SIZE = 256  # Standard size for substitution boxes
	
	def __init__(self, config: XRScramblerConfig):
		self._init(config)
	
	def _init(self, config: XRScramblerConfig):
		if config == XRScramblerConfig.CC_RU:
			self.m_seed = self.SEED_RU
			self._init_sboxes(self.SEED0_RU, self.SIZE_MULT_RU)
		elif config == XRScramblerConfig.CC_WW:
			self.m_seed = self.SEED_WW
			self._init_sboxes(self.SEED0_WW, self.SIZE_MULT_WW)
		else:
			raise UnknownConfig()
	
	def _init_sboxes(self, seed: int, size_mult: int):
		# Initialize encryption sbox with sequential values
		m_enc_sbox, m_dec_sbox = bytearray(b'0' * self.SBOX_SIZE), bytearray(b'0' * self.SBOX_SIZE)
		for i in range(self.SBOX_SIZE - 1, -1, -1):
			m_enc_sbox[i] = i & 0xff
		
		# Scramble the sbox
		for i in range(size_mult * self.SBOX_SIZE, 0, -1):
			seed = (1 + seed * self.SEED_MULT) & 0xFFFFFFFF
			if seed & 0x80000000:
				# negative value # correct negative bit-shift operation
				seed = (seed & 0x7FFFFFFF) - 0x80000000
			a = (seed >> 24) & 0xff
			while True:
				seed = (1 + seed * self.SEED_MULT) & 0xFFFFFFFF
				if seed & 0x80000000:
					# negative value # correct negative bit-shift operation
					seed = (seed & 0x7FFFFFFF) - 0x80000000
				b = (seed >> 24) & 0xff
				if a != b:
					break
			
			# Swap elements
			m_enc_sbox[a], m_enc_sbox[b] = m_enc_sbox[b], m_enc_sbox[a]

			# for debug purposes
			# print(str(i).zfill(4), ' '.join(tuple((f'{hex(ii)[2:].zfill(2)}={hex(x)[2:].zfill(2)}' for ii, x in enumerate(m_enc_sbox) if ii != x))))
		
		# Create decryption sbox
		for i in range(self.SBOX_SIZE):
			m_dec_sbox[m_enc_sbox[i]] = i & 0xff

		self.m_dec_sbox, self.m_enc_sbox = bytes(m_dec_sbox), bytes(m_enc_sbox)

		# write_to_file('m_dec_sbox.bin', self.m_dec_sbox)
		# write_to_file('m_enc_sbox.bin', self.m_enc_sbox)

	def decrypt(self, src: bytes) -> bytes:
		dest = bytearray(b'0' * len(src))
		seed = self.m_seed
		for i in range(len(src)):
			seed = (1 + seed * self.SEED_MULT) & 0xFFFFFFFF
			if seed & 0x80000000:
				# negative value # correct negative bit-shift operation
				seed = (seed & 0x7FFFFFFF) - 0x80000000
			dest[i] = self.m_dec_sbox[src[i] ^ ((seed >> 24) & 0xff)]
		return dest

	def encrypt(self, src: bytes) -> bytes:
		dest = bytearray(b'0' * len(src))
		seed = self.m_seed
		for i in range(len(src)):
			seed = 1 + seed * self.SEED_MULT
			seed &= 0xFFFFFFFF
			dest[i] = self.m_enc_sbox[src[i]] ^ ((seed >> 24) & 0xff)
		return dest


# Test
if __name__ == "__main__":
	print('Scrambler test')
	print('Write binary files: src -> scramble.decrypt -> dst')

	TEST_DATA_LEN = 512

	def write_to_file(file_name: str, buff: bytes):
		print(f'\twrite to file: {file_name}')
		with open(file_name, 'wb') as f:
			f.write(buff)

	print('CC_RU')
	scrambler = XRScrambler(XRScramblerConfig.CC_RU)
	src = bytes((x & 0xFF for x in range(TEST_DATA_LEN)))
	dst = scrambler.decrypt(src)
	write_to_file('CC_RU.src.bin', src)
	write_to_file('CC_RU.dst.bin', dst)
