#!/bin/bash

if [ -z $ROOT_PASSWORD ]; then ROOT_PASSWORD=Root123; fi;

echo "Running flower via celery"
celery -A tasks flower --basic_auth=root:${ROOT_PASSWORD}
echo "Done flower run"
