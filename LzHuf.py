
# LzHuff compression/decompression. Lempel-Ziv-Huffman by Haruyasu Yoshizaki.
# Author: Stalker tools, 2023-2025

# Constants
N = 4096
F = 60
THRESHOLD = 2
MAX_FREQ = 0x4000

NIL = N
N_CHAR = 256 - THRESHOLD + F
T = N_CHAR * 2 - 1
R = T - 1

class WrongDataFormat(Exception): pass


class LzHuf:

	def __init__(self):
		self.freq = [0] * (T + 1)
		self.son = [0] * T
		self.prnt = [0] * (T + N_CHAR)
		self.text_buf = [0] * (N + F - 1)
		# self.d_code = [0] * 256
		# self.d_len = [0] * 256
		# Initialize d_code and d_len arrays (you'll need to populate these with actual values)
		self.d_code = \
			b'\x00\x00\x00\x00\x00\x00\x00\x00' + \
			b'\x00\x00\x00\x00\x00\x00\x00\x00' + \
			b'\x00\x00\x00\x00\x00\x00\x00\x00' + \
			b'\x00\x00\x00\x00\x00\x00\x00\x00' + \
			b'\x01\x01\x01\x01\x01\x01\x01\x01' + \
			b'\x01\x01\x01\x01\x01\x01\x01\x01' + \
			b'\x02\x02\x02\x02\x02\x02\x02\x02' + \
			b'\x02\x02\x02\x02\x02\x02\x02\x02' + \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x08\x08\x08\x08\x08\x08\x08\x08' + \
			b'\x09\x09\x09\x09\x09\x09\x09\x09' + \
			b'\x0A\x0A\x0A\x0A\x0A\x0A\x0A\x0A' + \
			b'\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B' + \
			b'\x0C\x0C\x0C\x0C\x0D\x0D\x0D\x0D' + \
			b'\x0E\x0E\x0E\x0E\x0F\x0F\x0F\x0F' + \
			b'\x10\x10\x10\x10\x11\x11\x11\x11' + \
			b'\x12\x12\x12\x12\x13\x13\x13\x13' + \
			b'\x14\x14\x14\x14\x15\x15\x15\x15' + \
			b'\x16\x16\x16\x16\x17\x17\x17\x17' + \
			b'\x18\x18\x19\x19\x1A\x1A\x1B\x1B' + \
			b'\x1C\x1C\x1D\x1D\x1E\x1E\x1F\x1F' + \
			b'\x20\x20\x21\x21\x22\x22\x23\x23' + \
			b'\x24\x24\x25\x25\x26\x26\x27\x27' + \
			b'\x28\x28\x29\x29\x2A\x2A\x2B\x2B' + \
			b'\x2C\x2C\x2D\x2D\x2E\x2E\x2F\x2F' + \
			b'\x30\x31\x32\x33\x34\x35\x36\x37' + \
			b'\x38\x39\x3A\x3B\x3C\x3D\x3E\x3F'

		self.d_len = \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x03\x03\x03\x03\x03\x03\x03\x03' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x04\x04\x04\x04\x04\x04\x04\x04' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x05\x05\x05\x05\x05\x05\x05\x05' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x06\x06\x06\x06\x06\x06\x06\x06' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x07\x07\x07\x07\x07\x07\x07\x07' + \
			b'\x08\x08\x08\x08\x08\x08\x08\x08' + \
			b'\x08\x08\x08\x08\x08\x08\x08\x08'

		self.getbuf = 0
		self.getlen = 0
		self.m_src = None
		self.m_src_pos = 0
		self.m_src_limit = 0
		self.m_dest = None
		self.m_dest_pos = 0
		self.m_dest_limit = 0
		self.textsize = 0
		self.codesize = 0

	def StartHuff(self):
		# print('		-> StartHuff')

		for i in range(N_CHAR):
			self.freq[i] = 1
			self.son[i] = i + T
			self.prnt[i + T] = i
		
		i, j = 0, N_CHAR
		while j <= R:
			self.freq[j] = self.freq[i] + self.freq[i + 1]
			self.son[j] = i
			self.prnt[i] = self.prnt[i + 1] = j
			i += 2
			j += 1
		
		self.freq[T] = 0xffff
		self.prnt[R] = 0

	def GetBit(self):
		# print(f'\t\t\t\t-> GetBit')
		# print(f'\t\t\t\tgetbuf={self.getbuf} (int)getlen={self.getlen}')
		while self.getlen <= 8:
			i = self.getc()
			if i < 0:
				i = 0
			# print(f'\t\t\t\t{i=} getbuf={self.getbuf} (int)getlen={self.getlen}')
			self.getbuf |= i << (8 - self.getlen)
			self.getbuf &= 0xFFFFFFFF
			self.getlen += 8
			# print(f'\t\t\t\tgetbuf={self.getbuf} (int)getlen={self.getlen}')
		
		i = self.getbuf
		# print(f'\t\t\t\tgetbuf={self.getbuf} (int)getlen={self.getlen}')
		self.getbuf <<= 1
		self.getbuf &= 0xFFFFFFFF
		self.getlen -= 1
		if i & 0x80000000:
			# negative value # correct negative bit-shift operation
			i = (i & 0x7FFFFFFF) - 0x80000000
		# print(f'\t\t\t\tgetbuf={self.getbuf} (int)getlen={self.getlen} {i=} {(i >> 15) & 1=}')
		return (i >> 15) & 1

	def getc(self):
		# print('\t\t\t\t-> getc')
		# print('\t\t\t\tm_src_pos{self.m_src_pos} m_src_limit{self.m_src_limit}')
		if self.m_src_pos < self.m_src_limit:
			c = self.m_src[self.m_src_pos]
			self.m_src_pos += 1
			return c
		else:
			return -1

	def DecodeChar(self):
		# print('\t\t-> DecodeChar')
		# print(f'\t\tson[R]={self.son[R]}')

		c = self.son[R]
		
		# travel from root to leaf,
		# choosing the smaller child node (son[]) if the read bit is 0,
		# the bigger (son[]+1) if 1
		while c < T:
			c += self.GetBit()
			# print(f'\t\t{c=} son[c]={self.son[c]}')
			c = self.son[c]
		
		c -= T
		# print(f'\t\t{c=}')
		self.update(c)
		# print(f'\t\t{c=}')
		return c

	def putc(self, c):
		# print('\t\t-> putc')
		# print(f'\t\t{c=} m_dest_pos={self.m_dest_pos} m_dest_limit{self.m_dest_limit} m_dest_pos >= m_dest_limit={self.m_dest_pos >= self.m_dest_limit}')
		if self.m_dest_pos >= self.m_dest_limit:
			# In Python, we would handle dynamic resizing differently
			# This is a simplified version
			new_limit = self.m_dest_limit * 2
			# print(f'\t\tm_dest_limit{self.m_dest_limit}')
			new_dest = bytearray(new_limit)
			new_dest[:self.m_dest_limit] = self.m_dest
			self.m_dest = new_dest
			self.m_dest_limit = new_limit
		
		self.m_dest[self.m_dest_pos] = c
		self.m_dest_pos += 1
		# print(f'\t\t{c=} m_dest_pos={self.m_dest_pos} m_dest_limit{self.m_dest_limit}')

	def GetByte(self):
		while self.getlen <= 8:
			c = self.getc()
			i = 0 if c < 0 else c
			self.getbuf |= i << (8 - self.getlen)
			self.getlen += 8
		
		i = self.getbuf
		self.getbuf <<= 8
		self.getlen -= 8
		return (i & 0xff00) >> 8

	def DecodePosition(self):
		# recover upper 6 bits from table

		# print('\t\t-> DecodePosition')

		i = self.GetByte()
		c = self.d_code[i] << 6
		j = self.d_len[i]
		
		# read lower 6 bits verbatim
		j -= 2
		while j > 0:
			i = (i << 1) + self.GetBit()
			j -= 1
		
		return c | (i & 0x3f)

	def reconst(self):
		# collect leaf nodes in the first half of the table
		# and replace the freq by (freq + 1) / 2.
		j = 0
		for i in range(T):
			if self.son[i] >= T:
				self.freq[j] = (self.freq[i] + 1) // 2
				self.son[j] = self.son[i]
				j += 1
		
		# begin constructing tree by connecting sons
		i = 0
		j = N_CHAR
		while j < T:
			k = i + 1
			f = self.freq[j] = self.freq[i] + self.freq[k]
			k = j - 1
			while f < self.freq[k]:
				k -= 1
			k += 1
			l = (j - k)
			
			# Shift elements to make room (equivalent to memmove)
			for idx in range(j, k, -1):
				self.freq[idx] = self.freq[idx - 1]
			self.freq[k] = f
			
			for idx in range(j, k, -1):
				self.son[idx] = self.son[idx - 1]
			self.son[k] = i
			
			i += 2
			j += 1
		
		# connect prnt
		for i in range(T):
			k = self.son[i]
			if k >= T:
				self.prnt[k] = i
			else:
				self.prnt[k] = self.prnt[k + 1] = i

	def update(self, c):
		# increment frequency of given code by one, and update tree
		# print('\t\t\t-> update')
		# print(f'\t\t\t{self.freq[R]=} {MAX_FREQ=}')

		if self.freq[R] == MAX_FREQ:
			self.reconst()
		
		c = self.prnt[c + T]
		while True:
			# print(f'\t\t\t{c=} freq[c]={self.freq[c]}')
			k = self.freq[c] + 1
			self.freq[c] = k
			# print(f'\t\t\t{c=} freq[c]={self.freq[c]}')
			
			# if the order is disturbed, exchange nodes
			l = c + 1
			if k > self.freq[l]:
				while k > self.freq[l + 1]:
					l += 1
				
				self.freq[c] = self.freq[l]
				self.freq[l] = k
				
				i = self.son[c]
				self.prnt[i] = l
				if i < T:
					self.prnt[i + 1] = l
				
				j = self.son[l]
				self.son[l] = i
				
				self.prnt[j] = c
				if j < T:
					self.prnt[j + 1] = c
				self.son[c] = j
				
				c = l
			
			# print(f'\t\t\t{c=} prnt[c]={self.prnt[c]}')
			c = self.prnt[c]
			if c == 0:  # repeat up to root
				break

	def Decode(self, code: bytes) -> bytes:
		# recover
		# print('\t-> Decode')
		if len(code) < 4:
			raise WrongDataFormat()
		self.textsize = int.from_bytes(code[0:4], byteorder='little')
		self.m_dest = bytearray(self.textsize)
		self.m_dest_pos = 0
		self.m_dest_limit = self.textsize
		
		self.m_src_limit = len(code)
		self.m_src = code
		self.m_src_pos = 4
		
		self.getbuf = 0
		self.getlen = 0
		
		self.StartHuff()
		
		for i in range(N - F):
			self.text_buf[i] = ord(' ')
		
		r = N - F
		count = 0
		
		while count < self.textsize:
			# print(f'\t{count=}')
			c = self.DecodeChar()
			# print(f'\t{c=} {c < 256=}')
			if c < 256:
				self.putc(c)
				self.text_buf[r] = c
				r += 1
				r &= (N - 1)
				count += 1
			else:
				i = (r - self.DecodePosition() - 1) & (N - 1)
				j = c - 255 + THRESHOLD
				# print(f'\t{i=} {j=}')
				for k in range(j):
					c = self.text_buf[(i + k) & (N - 1)]
					self.putc(c)
					self.text_buf[r] = c
					r += 1
					r &= (N - 1)
					count += 1
		
		return bytes(self.m_dest[:self.textsize])


if __name__ == "__main__":
	import argparse
	from sys import argv, stdout
	from os.path import basename
	from pathlib import Path

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='LzHuf test (LzHuf decompression) to decode binary chunks',
				epilog=f'''Examples:
	decode binary file (LzHuf decompression):
{basename(argv[0])} -f "gamedata.dbd.header-decrypted.bin" d > "gamedata.dbd.header-decoded.bin"
	decode binary file with human-readable output:
{basename(argv[0])} -v -f "gamedata.dbd.header-decrypted.bin" d > "gamedata.dbd.header-decoded.bin"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-f', metavar='PATH', required=True, help='binary file path')
			parser.add_argument('-v', action='store_true', help='verbose mode')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			subparsers.add_parser('decode', aliases=('d',), help='decode')
			return parser.parse_args()

		args = parse_args()
		verbose = args.v

		if verbose:
			print(f'File: {Path(args.f).name}')
			print(f'size: {Path(args.f).stat().st_size:_}')

		match args.mode:
			case 'decode' | 'd':
				lz_huf = LzHuf()
				with open(args.f, 'rb') as f:
					buff = lz_huf.Decode(f.read())
					if verbose:
						print(f'Output:')
						print(f'size: {len(buff):_}')
						print(buff)
					else:
						stdout.buffer.write(buff)

	try:
		main()
	except WrongDataFormat:
		print('WrongDataFormat')
	except BrokenPipeError: pass
