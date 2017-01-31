#!/bin/bash -e

export RELEASE_VERSION=`date +"%Y%m%d%H%M%S"`
tar -czf oclapi$RELEASE_VERSION.tgz repo
scp oclapi$RELEASE_VERSION.tgz root@$IP:/root/releases/
if ssh root@$IP "~/oclapi/django-nonrel/ocl/deploy/kill_docker.sh"; then echo "killed docker processes"; fi;
ssh root@$IP "rm -rf oclapi"
ssh root@$IP "tar -xzf releases/oclapi$RELEASE_VERSION.tgz && mv repo oclapi"
ssh root@$IP "chmod -R 777 oclapi/solr/collection1"
if ssh root@$IP "~/oclapi/django-nonrel/ocl/deploy/manage_releases.sh clear_releases"; then echo "Removed old releases"; fi;
ssh root@$IP "~/oclapi/django-nonrel/ocl/deploy/start_docker.sh"
ssh root@$IP "docker ps"