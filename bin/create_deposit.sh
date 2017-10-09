#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../deposit.zip'}

NAME=$(basename ${ARCHIVE})
MD5=$(md5sum ${ARCHIVE} | cut -f 1 -d' ')

PROGRESS=${2-'false'}

curl -i -u "$CREDS" \
     -X POST \
     --data-binary @${ARCHIVE} \
     -H "In-Progress: ${PROGRESS}" \
     -H "Content-MD5: ${MD5}" \
     -H "Content-Disposition: attachment; filename=${NAME}" \
     -H 'Slug: external-id' \
     -H 'Packaging: http://purl.org/net/sword/package/SimpleZip' \
     -H 'Content-type: application/zip' \
     ${SERVER}/1/${COLLECTION}/
