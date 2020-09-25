#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}
ARCHIVE=${2-'../../swh-core.zip'}

NAME=$(basename ${ARCHIVE})
MD5=$(md5sum ${ARCHIVE} | cut -f 1 -d' ')
PROGRESS=${3-'false'}

curl -i -u "${CREDS}" \
     -X POST \
     --data-binary @${ARCHIVE} \
     -H "In-Progress: ${PROGRESS}" \
     -H "Content-MD5: ${MD5}" \
     -H "Content-Disposition: attachment; filename=${NAME}" \
     -H 'Slug: external-id-2' \
     -H 'Packaging: http://purl.org/net/sword/package/SimpleZip' \
     -H 'Content-type: application/zip' \
     ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/media/
