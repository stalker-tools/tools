
export ZIPPED_PY_NAME=db-extract
export MAIN_FILE="paths.py"
export COPY_FILES="LzHuf.py DBReader.py LayeredFileSystem.py SequensorReader.py Scrambler.py version.py"

PUBLISH_PATH=./publish
"$PUBLISH_PATH/zippapp-create.sh"
