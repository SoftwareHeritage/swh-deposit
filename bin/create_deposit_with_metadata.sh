#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../deposit.zip'}
ATOM_ENTRY=${2-'../../atom-entry.xml'}
NAME=$(basename $ARCHIVE)

MD5=$(md5sum $ARCHIVE | cut -f 1 -d' ')

PROGRESS=${3-'false'}

curl -i --user "${CREDS}" \
     -F "file=@${ARCHIVE};type=application/zip;filename=payload" \
     -F "atom=@${ATOM_ENTRY};type=application/atom+xml;charset=UTF-8" \
     -H "In-Progress: ${PROGRESS}" \
     -H 'Slug: some-external-id' \
     -XPOST ${SERVER}/1/${COLLECTION}/
