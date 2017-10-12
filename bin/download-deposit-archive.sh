#!/usr/bin/env bash

. ./default-setup

DEPOSIT_ID=${1-1}

curl ${SERVER}/1/${COLLECTION}/${DEPOSIT_ID}/raw/
