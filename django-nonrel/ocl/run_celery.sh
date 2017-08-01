#!/bin/bash
echo "running celery"
AWS_ACCESS_KEY_ID=$1 AWS_SECRET_ACCESS_KEY=$2 AWS_STORAGE_BUCKET_NAME=$3 celery -A tasks worker --loglevel=INFO
echo "done celery run"
