#!/usr/bin/env bash

. ./default-setup

curl -i -u "${CREDS}" ${SERVER}/1/servicedocument/
