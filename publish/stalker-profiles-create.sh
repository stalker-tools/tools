
export ZIPPED_PY_NAME=stalker-profiles
export MAIN_FILE="profiles_tool.py"
export COPY_FILES="dialog_tool.py ltx_tool.py paths.py GameConfig.py icon_tools.py xml_tool.py localization.py LzHuf.py DBReader.py LayeredFileSystem.py SequensorReader.py Scrambler.py version.py"

PUBLISH_PATH=./publish
"$PUBLISH_PATH/zippapp-create.sh"
