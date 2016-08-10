#!/bin/bash
echo "running celery"
celery -A tasks worker --loglevel=info
echo "done celery run"
