#!/bin/bash -e
cd /root/oclapi/django-nonrel/ocl/
redis_keys=$(/usr/local/bin/docker-compose exec -T redis redis-cli keys "*celery*")
keys=($redis_keys)
len=${#keys[@]}
if [ $len -gt 1 ]
then
    logger ok
else
    logger restarting
    cd /root/oclapi/django-nonrel/ocl && echo $(/usr/local/bin/docker-compose -f docker-compose.yml restart ocl_worker) && logger end
fi
