
from io import BytesIO
from os import sep as path_separator
from os.path import join, basename, split


def xml_preprocessor(xml_file_path: str, include_base_path: str | None = None, included = False) -> bytes:
	'''features:
		- process #include to include text from another .xml files
		- removes comments <!-----> since they break W3C XML rules
		- removes <?xml tags in included documents since they break W3C XML rules
	'''

	buff = BytesIO()
	with open(xml_file_path, 'rb') as f:
		for line in f.readlines():
			if line.startswith(b'#include'):
				# include .xml file
				line = line[len(b'#include') + 1:].strip(b' \t\r\n').strip(b'"')
				line = line.replace(b'\\', path_separator.encode())  # convert path splitter to ext filesystem
				buff.write(xml_preprocessor(join(include_base_path if include_base_path else split(xml_file_path)[0], line.decode()), include_base_path, True))
			elif line.lstrip().startswith(b'<!--'):
				continue
			elif included and line.startswith(b'<?xml'):
				continue
			else:
				buff.write(line)
	return buff.getvalue()


if __name__ == '__main__':
	import argparse
	from sys import argv, stdout

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''X-ray xml proprocessor. Features:
 - process #include to include text from another .xml files
 - removes comments <!-----> since they break W3C XML rules
 - removes <?xml tags in included documents since they break W3C XML rules''',
				epilog=f'''Examples:
{basename(argv[0])} "$HOME/.wine/drive_c/Program Files (x86)/Sigerous Mod/gamedata/configs/text/rus/SGM_add_include.xml" > "sgm_localization.xml"''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-i', metavar='PATH', help='include base path')
			parser.add_argument('file', metavar='XML_FILE_PATH', help='.xml file to preprocess')
			return parser.parse_args()

		args = parse_args()

		stdout.buffer.write(xml_preprocessor(args.file, args.i))

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
