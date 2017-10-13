#!/usr/bin/env bash

. ./default-setup

ATOM=${1-'../../atom.xml'}
PROGRESS=${2-'false'}

curl -i -u "$CREDS" \
     --data-binary @${ATOM} \
     -X POST \
     -H "In-Progress: ${PROGRESS}" \
     -H 'Content-Type: application/atom+xml;type=entry' \
     -H 'Slug: external-id' \
     -H 'Packaging: http://purl.org/net/sword/package/SimpleZip' \
     ${SERVER}/1/${COLLECTION}/
