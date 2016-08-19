#!/bin/bash

cd ~/oclapi/django-nonrel/ocl && docker-compose -f docker-compose.$1.yml build && docker-compose -f docker-compose.$1.yml up -d
