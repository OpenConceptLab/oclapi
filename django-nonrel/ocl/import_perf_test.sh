#!/bin/bash
python manage.py syncdb --noinput
#create org and source
OBJECT_ID=`mongo ocl perf_data/prepare_db.js | grep ObjectId`
SOURCE=`expr substr $OBJECT_ID 11 24`
start=`date +%s`
yes | python manage.py rebuild_index
#first time import
python manage.py import_concepts_to_source --source $SOURCE --token PERF_TEST_TOKEN perf_data/ciel_20160711_concepts_2k.json
yes | python manage.py rebuild_index
end=`date +%s`
runtime=$((end-start))
echo "Took $(runtime) sec to complete concepts"
# python manage.py import_mappings_to_source --source 572343325162890014a3424b --token PERF_TEST_TOKEN perf_data/ciel_20160711_mappings_2k.json
