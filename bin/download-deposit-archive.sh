#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}

curl -u "$CREDS" ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/raw/
