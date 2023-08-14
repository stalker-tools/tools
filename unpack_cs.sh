#!/usr/bin/env bash
# Unpack Clear Sky to gamedata folder

if [ -z ${GAME_PATH} ] || [ -z ${CONVERTER_PATH} ]; then
	echo "Environ variables not defined: GAME_PATH, CONVERTER_PATH"
	echo "	GAME_PATH - path to game; example:"
	echo "export GAME_PATH=\"\$HOME/.wine/drive_c/Program Files (x86)/clear_sky/\""
	echo "	CONVERTER_PATH - path to converter.exe; example:"
	echo "export CONVERTER_PATH=\"\$HOME/.wine/drive_c/Program Files (x86)/converter_25aug2008/converter.exe\""
	exit 1
fi

find "$GAME_PATH""resources" -type f -exec echo -e "\nEXTRACT: ""{}" \; -exec wine "$CONVERTER_PATH" -unpack -xdb "{}" -dir "$GAME_PATH""gamedata" \;

find "$GAME_PATH""patches" -type f -exec echo -e "\nEXTRACT: ""{}" \; -exec wine "$CONVERTER_PATH" -unpack -xdb "{}" -dir "$GAME_PATH""gamedata" \;
