#!/bin/bash

cd ~/oclapi/django-nonrel/ocl && docker-compose -f docker-compose.$1.yml build ocl ocl_worker solr && docker-compose -f docker-compose.$1.yml up -d