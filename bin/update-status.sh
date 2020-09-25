#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}
UPDATE_STATUS=${2-'done'}

curl -i \
     -X PUT \
     -H 'Content-Type: application/json' \
     -d "{\"status\": \"${UPDATE_STATUS}\"}" \
     ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/update/
