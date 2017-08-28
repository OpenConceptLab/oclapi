#!/bin/bash
echo "Running celery"
celery -A tasks worker --loglevel=INFO
echo "Done celery run"
