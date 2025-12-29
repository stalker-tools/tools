
PUBLISH_PATH=./publish

TEMP_DIR_PATH="$PUBLISH_PATH/standalon.out"
if [ ! -d "$TEMP_DIR_PATH" ]; then
	echo "Create temp out dir: $TEMP_DIR_PATH"
	mkdir -v "$TEMP_DIR_PATH"
fi

$PUBLISH_PATH/py_pack -v -fu "$TEMP_DIR_PATH/$ZIPPED_PY_NAME" -m $MAIN_FILE -s $COPY_FILES -c "Stalker tools .db/.xdb $ZIPPED_PY_NAME $(date -R)"
