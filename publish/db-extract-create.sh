
ZIPPED_PY_NAME=db-extract
MAIN_FILE="paths.py"
COPY_FILES="LzHuf.py DBReader.py LayeredFileSystem.py SequensorReader.py Scrambler.py version.py"

PUBLISH_PATH=./publish

TEMP_DIR_PATH="$PUBLISH_PATH/$ZIPPED_PY_NAME.out"
echo "Create temp dir: $TEMP_DIR_PATH"
mkdir "$TEMP_DIR_PATH"

$PUBLISH_PATH/py_pack -v -fu "$TEMP_DIR_PATH/$ZIPPED_PY_NAME" -m paths.py -s $COPY_FILES -c "Stalker tools .db/.xdb db-extract $(date -R)"
