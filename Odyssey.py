#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Stalker tools and Odyssey main game tools
# Author: Stalker tools, 2023-2024

from typing import Iterator
from dataclasses import dataclass
from Game import Game as XrayGame


class OdysseyMissingInstance(Exception): pass


# Odyssey event API classes: decorators and data clases

def on_map_entry(func):
	if (od := Odyssey.instance):
		od.on_map_changed.append(func)
	else: raise(OdysseyMissingInstance)


@dataclass
class MapChanged:
	map_name: str
	first_enter: bool
	def iter_actor_objects(self, actor_only=False) -> Iterator[dict]:
		pass
	def has_actor_object(self, name: str) -> bool:
		pass


# Odyssey game class


class Odyssey:

	instance: 'Odyssey' = None

	def __init__(self, game: XrayGame):
		self.game = game
		Odyssey.instance = self  # for decorators
		# game event callbacks
		self.on_map_changed: list[callable] = []

	def map_changed(self, data: MapChanged):
		'on game map (level) changed'
		for ev in self.on_map_changed:
			ev(data)

	# virtual methods

	def set_radio_audio(self, file_path: str): pass
