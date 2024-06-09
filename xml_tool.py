
from sys import stderr
from io import BytesIO
from os import sep as path_separator
from os.path import join, basename, split
from xml.dom.minidom import parseString, Element, Document


def xml_preprocessor(xml_file_path: str, include_base_path: str | None = None, included = False, failed_include_file_paths: list[str] = None) -> bytes:
	'''features:
		- process #include to include text from another .xml files
		- removes comments <!-----> since they break W3C XML rules
		- removes <?xml tags in included documents since they break W3C XML rules
	'''

	buff = BytesIO()
	with open(xml_file_path, 'rb') as f:
		for line in f.readlines():
			line_stripped = line.lstrip()
			if line_stripped.startswith(b'#include'):
				# include .xml file
				line_stripped = line_stripped[len(b'#include') + 1:].strip(b' \t\r\n').strip(b'"')
				line_stripped = line_stripped.replace(b'\\', path_separator.encode())  # convert path splitter to ext filesystem
				include_file_path = join(include_base_path if include_base_path else split(xml_file_path)[0], line_stripped.decode())
				try:
					buff.write(xml_preprocessor(include_file_path, include_base_path, True))
				except FileNotFoundError:
					if failed_include_file_paths is not None:
						if include_file_path in failed_include_file_paths:
							continue
						failed_include_file_paths.append(include_file_path)
					print(f'include file not found: {include_file_path}', file=stderr)
			elif line_stripped.startswith(b'<!--'):
				continue
			elif included and line.startswith(b'<?xml'):
				continue
			else:
				buff.write(line)
	return buff.getvalue()

def xml_parse(xml_file_path: str, include_base_path: str | None = None, included = False, failed_include_file_paths: list[str] = None) -> Document:
	'''features:
		- process #include to include text from another .xml files
		- removes comments <!-----> since they break W3C XML rules
		- removes <?xml tags in included documents since they break W3C XML rules
	'''
	buff = xml_preprocessor(xml_file_path, include_base_path, included, failed_include_file_paths)
	return parseString(buff)

def iter_child_elements(element: Element):
	for e in (x for x in element.childNodes if type(x) == Element):
		yield e

def get_child_by_id(element: Element, child_name: str, id: str) -> Element | None:
	for e in element.getElementsByTagName(child_name):
		if (e_id := e.getAttribute('id')) and e_id == id:
			return e
	return None

def get_child_element_values(element: Element, child_name: str, join_str: str | None = None) -> list[str] | str:
	ret = []
	for e in element.getElementsByTagName(child_name):
		if (e := e.firstChild):
			ret.append(e.nodeValue)
	return join_str.join(ret) if join_str is not None else ret


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
