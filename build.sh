#!/bin/bash
set -e
set -x

if [ -z "$VERSION" ]; then
    [ -z "$(git tag -l | head -1)" ] && git tag 0.0.1
    export VERSION="$(poetry version | awk '{print $2}')"
fi

rm -rf ./dist ./build || true

poetry check
poetry install
poetry show

# build single file executable
poetry export -f requirements.txt --output requirements.txt --without-hashes
pip install pyinstaller
sed -ri "s/VERSION *= *['\"].*['\"]/VERSION = \"${VERSION}\"/" ./backupdirsm/main.py
grep 'VERSION = ' ./backupdirsm/main.py
pyinstaller --clean --noupx --onefile backupdirsm/main.py

# pyi-archive_viewer -l dist/main

cp ./dist/main ./dist/backupdirsm
ls -pilaF ./dist

# poetry build after VERSION patched
poetry build
