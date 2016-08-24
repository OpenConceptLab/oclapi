#!/bin/bash

export DJANGO_CONFIGURATION=Staging
#create org and source
OBJECT_ID=`mongo ocl perf_data/prepare_bulk_import_db_with_root_user.js | grep ObjectId`
SOURCE=`expr substr $OBJECT_ID 11 24`
ssh root@$1 "time docker-compose run ocl python manage.py import_concepts_to_source --source $SOURCE --token $2 --inline-indexing true ~/ciel_20160711/ciel_20160711_concepts.json"
ssh root@$1 "time docker-compose run ocl python manage.py import_mappings_to_source --source $SOURCE --token $2 --inline-indexing true ~/ciel_20160711/ciel_20160711_mappings.json"