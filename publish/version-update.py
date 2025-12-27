#!/usr/bin/env python3

# Writes version.py file by git version: see git_command variable

from datetime import datetime
from subprocess import check_output

git_command = 'git describe --tags --always --dirty --long'

git_version = check_output(git_command.split(' ')).strip()
if not git_version:
	raise ValueError(f'Can\'t get version from fit: this is not git repository or git not installed')

print(f'New version: {git_version.decode()}')

with open('version.py', 'wb') as f:
	f.write(b'# This is automatic generated file. Do not edit.\n')
	f.write(b'# ')
	f.write(datetime.now().isoformat().encode())
	f.write(b'\n')
	f.write(b'VERSION = \'')
	f.write(git_version)
	f.write(b'\'\n')
