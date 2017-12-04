#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../swh-deposit.zip'}
ATOM_ENTRY=${2-'../../atom-entry.xml'}

NAME=$(basename $ARCHIVE)
MD5=$(md5sum $ARCHIVE | cut -f 1 -d' ')

PROGRESS=${3-'false'}
EXTERNAL_ID=${4-'external-id'}

set -x
curl -i --user "${CREDS}" \
     -H "In-Progress: ${PROGRESS}" \
     -H "Slug: ${EXTERNAL_ID}" \
     -F "file=@${ARCHIVE};type=application/zip" \
     -F "atom=@${ATOM_ENTRY};type=application/atom+xml;type=entry" \
     -XPOST ${SERVER}/1/${COLLECTION}/
