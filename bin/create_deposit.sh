#!/usr/bin/env bash

. ./default-setup

ARCHIVE=${1-'../../deposit.zip'}

STATUS=${2-'--no-partial'}

./swh-deposit \
        --username ${USER} \
        --password ${PASSWORD} \
        --collection ${COLLECTION} \
        --archive-deposit \
        --archive ${ARCHIVE} \
        ${STATUS} \
        --url ${SERVER}/1
