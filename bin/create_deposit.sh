#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../deposit.zip'}

NAME=$(basename ${ARCHIVE})
MD5=$(md5sum ${ARCHIVE} | cut -f 1 -d' ')

PROGRESS=${2-'false'}
TYPE=${3-'application/zip'}

curl -i -u "$CREDS" \
     -X POST \
     --data-binary @${ARCHIVE} \
     -H "In-Progress: ${PROGRESS}" \
     -H "Content-MD5: ${MD5}" \
     -H "Content-Disposition: attachment; filename=${NAME}" \
     -H 'Slug: external-id' \
     -H "Content-type: ${TYPE}" \
     ${SERVER}/1/${COLLECTION}/
