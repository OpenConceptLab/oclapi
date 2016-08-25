#!/bin/bash -e
SOURCE=`sh ./export_vars_for_import_script`
export DJANGO_CONFIGURATION=Staging
echo "Importing in Source -- $SOURCE"
time docker-compose run ocl python manage.py import_concepts_to_source --source $SOURCE --token $1 --inline-indexing true ciel_20160711/ciel_20160711_concepts.json
time docker-compose run ocl python manage.py import_mappings_to_source --source $SOURCE --token $1 --inline-indexing true ciel_20160711/ciel_20160711_mappings.json