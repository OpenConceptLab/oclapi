#!/bin/bash -e

BULK_IMPORT_SCRIPT="`cat perf_data/prepare_bulk_import_db_with_root_user.js`"
echo $BULK_IMPORT_SCRIPT
OBJECT_ID=`docker exec -t ocl_mongo mongo ocl --eval "$BULK_IMPORT_SCRIPT" | grep ObjectId`
echo $OBJECT_ID
SOURCE=`echo $OBJECT_ID | cut -c 11-34`
export DJANGO_CONFIGURATION=Staging
echo "Importing in Source -- $SOURCE"
time docker-compose run ocl python manage.py import_concepts_to_source --source $SOURCE --token $1 --inline-indexing true ciel_20160711/ciel_20160711_concepts.json
time docker-compose run ocl python manage.py import_mappings_to_source --source $SOURCE --token $1 --inline-indexing true ciel_20160711/ciel_20160711_mappings.json