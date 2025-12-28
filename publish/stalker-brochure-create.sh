
ZIPPED_PY_NAME=stalker-brochure
MAIN_FILE="graph_tool.py"
COPY_FILES="ltx_tool.py paths.py GameConfig.py icon_tools.py xml_tool.py localization.py LzHuf.py DBReader.py LayeredFileSystem.py SequensorReader.py Scrambler.py version.py"

PUBLISH_PATH=./publish

TEMP_DIR_PATH="$PUBLISH_PATH/standalon.out"
echo "Create temp dir: $TEMP_DIR_PATH"
mkdir "$TEMP_DIR_PATH"

$PUBLISH_PATH/py_pack -v -fu "$TEMP_DIR_PATH/$ZIPPED_PY_NAME" -m $MAIN_FILE -s $COPY_FILES -c "Stalker tools .db/.xdb $ZIPPED_PY_NAME $(date -R)"
