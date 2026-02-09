#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Stalker tools, 2023-2026

from glob import glob
from pathlib import Path
from PIL.Image import open as image_open
from PIL import Image
import cv2
import numpy as np
# stalker-tools import
try:
	from version import PUBLIC_VERSION, PUBLIC_DATETIME
except ModuleNotFoundError: PUBLIC_VERSION, PUBLIC_DATETIME = '', ''


def dds_to_video(dds_file_pattern: str, video_file_path: str, fps: int, fourcc: str):
	'converts .dds files with name pattern to video file'
	video = frame_size = None
	frames_count = 0
	for file_path in sorted(glob(dds_file_pattern)):
		if (frame := image_open(file_path)):
			if video is None:
				frame_size = (frame.width, frame.height)
				fourcc = cv2.VideoWriter_fourcc(*fourcc)
				video = cv2.VideoWriter(video_file_path, fourcc, fps, (frame_size[0], frame_size[1]))
			if frame.width == frame_size[0] and frame.height == frame_size[1]:
				frames_count += 1
				frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
				video.write(np.array(frame))
			else:
				print(f'Drop frame since it mismatch size: {file_path}')
		else:
			print(f'Drop file since it not image: {file_path}')
	print(f'Save frames count: {frames_count}')

def video_to_dds(video_file_path: str, dds_file_pattern: str, fps: int, fourcc: str):
	'converts video file to .dds files with name pattern'
	if (video := cv2.VideoCapture(video_file_path)) and video.isOpened():
		frames_count = 0
		while True:
			ret, frame = video.read()
			if not ret:
				break
			frames_count += 1
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			frame = Image.fromarray(frame)
			frame.save(dds_file_pattern.replace('*', f'{frames_count:03}'))
		print(f'Save images count: {frames_count}')
	else:
		print(f'Error while video file open: {video_file_path}')

if __name__ == '__main__':
	import argparse
	from sys import argv
	from os.path import basename

	DEFAULT_FPS = 4
	DEFAULT_FOURCC = 'MJPG'

	def main():

		def parse_args():
			parser = argparse.ArgumentParser(
				description='''Converter .dds to video and video to .dds. Used with video on tv.''',
				epilog=f'''Examples:

    Export tv video to .mkv file:
{basename(argv[0])} i2v ".../S.T.A.L.K.E.R/gamedata/textures/fx/fx_stalker_*.dds" ".../S.T.A.L.K.E.R/fx_stalker.mkv"

    Import tv video from .mkv file:
{basename(argv[0])} v2i ".../S.T.A.L.K.E.R/fx_stalker.mkv" ".../S.T.A.L.K.E.R/gamedata/textures/fx/fx_stalker_*.dds"
''',
				formatter_class=argparse.RawTextHelpFormatter
			)
			parser.add_argument('-F', '--fps', default=DEFAULT_FPS, help=f'video fps; default: {DEFAULT_FPS}')
			parser.add_argument('-C', '--fourcc', default=DEFAULT_FOURCC, help=f'video fourcc code, 4 bytes; default: {DEFAULT_FOURCC}')
			parser.add_argument('-V', action='version', version=f'{PUBLIC_VERSION} {PUBLIC_DATETIME}', help='show version')
			subparsers = parser.add_subparsers(dest='mode', help='sub-commands:')
			parser_ = subparsers.add_parser('i2v', help='images to video: .dds files to .avi video')
			parser_.add_argument('images', metavar='PATTERN', help='.dds files pattern')
			parser_.add_argument('video', metavar='FILE_PATH', help='out video file path')
			parser_ = subparsers.add_parser('v2i', help='video to images: .avi video file to .dds files')
			parser_.add_argument('video', metavar='FILE_PATH', help='out video file path')
			parser_.add_argument('images', metavar='PATTERN', help='.dds files pattern')
			return parser.parse_args()

		args = parse_args()

		match args.mode:
			case 'i2v':
				dds_to_video(args.images, args.video, args.fps, args.fourcc)
			case 'v2i':
				video_to_dds(args.video, args.images, args.fps, args.fourcc)

	try:
		main()
	except (BrokenPipeError, KeyboardInterrupt):
		exit(0)
