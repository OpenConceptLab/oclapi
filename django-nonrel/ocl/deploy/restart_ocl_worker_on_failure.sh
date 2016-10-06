#!/bin/bash
export redis_keys=`redis-cli keys "*celery*"`
keys=($redis_keys)
len=${#keys[@]}
if [ $len -gt 1 ]
then
echo 'ok!'
else
`cd ~/oclapi/django-nonrel/ocl && docker-compose -f docker-compose.yml restart ocl_worker`
fi
