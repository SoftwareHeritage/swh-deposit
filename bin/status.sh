#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}

./swh-deposit \
        --username ${USER} \
        --password ${PASSWORD} \
        --collection ${COLLECTION} \
        --status \
        --deposit-id ${DEPOSIT_ID} \
        --url ${SERVER}/1
