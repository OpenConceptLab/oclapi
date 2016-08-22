#!/bin/bash

cd ~/oclapi/django-nonrel/ocl && docker-compose build ocl ocl_worker solr && docker-compose up -d