#!/bin/bash

echo "Running flower via celery"
celery -A tasks flower
echo "Done flower run"
