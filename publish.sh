#!/bin/bash
set -e
set -x

: ${PYPI_TOKEN:?"ERROR: PYPI_TOKEN must be specified!"}
: ${PYPI_UPLOAD_URL:?"ERROR: PYPI_UPLOAD_URL must be specified!"}
: ${PYPI_CHECK_URL:?"ERROR: PYPI_CHECK_URL must be specified!"}

PYPI_REPO_NAME=$(echo "$PYPI_UPLOAD_URL" | awk -F[/:] '{print tolower($4)}' | tr -d '.')
PACKAGE_NAME=backupdirsm
VERSION=$(poetry version -s)

EXISTS=$(curl -fs ${PYPI_CHECK_URL}${PACKAGE_NAME}/${VERSION}/json || echo "not found")

if [[ $EXISTS == "not found" ]]; then
    echo "Version $VERSION does not exist, proceeding with upload."
    poetry config repositories.${PYPI_REPO_NAME} ${PYPI_UPLOAD_URL}
    poetry config pypi-token.${PYPI_REPO_NAME} ${PYPI_TOKEN}
    poetry publish --repository ${PYPI_REPO_NAME}
else
    echo "Version $VERSION already exists, skipping upload."
    exit 0
fi
