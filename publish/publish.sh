#!/usr/bin/env sh

# run it from git cloned 'tools' path

PUBLISH_PATH=./publish

echo "Create/update version.py"
$PUBLISH_PATH/version-update.py
echo

echo "Create db-extract"
$PUBLISH_PATH/db-extract-create.sh
