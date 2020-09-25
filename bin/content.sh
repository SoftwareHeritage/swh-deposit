#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}

curl -i -u "${CREDS}" ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/content/
