#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../swh-model.zip'}
NAME=$(basename ${ARCHIVE})

MD5=$(md5sum ${ARCHIVE} | cut -f 1 -d' ')

DEPOSIT_ID=${2-1}

curl -i -u "$CREDS" \
     -X PUT \
     --data-binary @${ARCHIVE} \
     -H "In-Progress: false" \
     -H "Content-MD5: ${MD5}" \
     -H "Content-Disposition: attachment; filename=${NAME}" \
     -H 'Slug: external-id' \
     -H 'Packaging: http://purl.org/net/sword/package/SimpleZip' \
     -H 'Content-type: application/zip' \
     ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/media/
