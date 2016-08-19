#!/bin/bash
echo "running celery"
celery -A tasks worker --loglevel=INFO
echo "done celery run"
