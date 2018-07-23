#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../swh-deposit.zip'}
ATOM_ENTRY=${2-'../../atom-entry.xml'}

STATUS=${3-'--no-partial'}
EXTERNAL_ID=${4-'external-id'}

./swh-deposit \
        --username ${USER} \
        --password ${PASSWORD} \
        --collection ${COLLECTION} \
        --archive-deposit \
        --archive ${ARCHIVE} \
        --metadata-deposit \
        --metadata ${ATOM_ENTRY} \
        --slug ${EXTERNAL_ID} \
        ${STATUS} \
        --url ${SERVER}/1
