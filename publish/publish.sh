#!/usr/bin/env sh

# run it from git cloned 'tools' path

PUBLISH_PATH=./publish

echo "Create/update version.py"
$PUBLISH_PATH/version-update.py
echo

echo "Create standalone apps: Python zipapps"

STANDALONE_APPS="db-extract stalker-brochure stalker-dialogs stalker-profiles stalker-tasks"

for STANDALONE_APP in $STANDALONE_APPS; do
	echo
	echo "Create $STANDALONE_APP"
	$PUBLISH_PATH/$STANDALONE_APP-create.sh
done
