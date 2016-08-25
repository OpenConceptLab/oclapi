#!/bin/bash

echo "running flower via celery"
celery -A tasks flower
echo "done flower run!!!"
