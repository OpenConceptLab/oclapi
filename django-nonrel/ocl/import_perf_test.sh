#!/bin/bash -e
export DJANGO_CONFIGURATION=IntegrationTest
python manage.py syncdb --noinput
#create org and source
OBJECT_ID=`mongo ocl perf_data/prepare_db.js | grep ObjectId`
SOURCE=`expr substr $OBJECT_ID 11 24`
yes | python manage.py rebuild_index
#first time import
start=`date +%s`
python manage.py import_concepts_to_source --source $SOURCE --token PERF_TEST_TOKEN perf_data/ciel_20160711_concepts_2k.json --configuration=Dev
yes | python manage.py rebuild_index -a 1
end=`date +%s`
runtime=$((end-start))
echo "Took ${runtime} sec to complete import concepts"
if [ $runtime -ge 120 ];
then
	echo >&2 "It has taken longer to import concepts"
	exit 1;
fi

start=`date +%s`
python manage.py import_mappings_to_source --source $SOURCE --token PERF_TEST_TOKEN perf_data/ciel_20160711_mappings_2k.json --configuration=Dev
yes | python manage.py rebuild_index -a 1
end=`date +%s`
runtime=$((end-start))
echo "Took ${runtime} sec to complete import mappings"
if [ $runtime -ge 420 ];
then
	echo >&2 "It has taken longer to import mappings"
	exit 1;
fi

#diff import
start=`date +%s`
python manage.py import_concepts_to_source --source $SOURCE --token PERF_TEST_TOKEN --inline-indexing true perf_data/ciel_20160711_concepts_2k.json
end=`date +%s`
runtime=$((end-start))
echo "Took ${runtime} sec to diff import concepts"
if [ $runtime -ge 30 ];
then
	echo >&2 "It has taken longer to re-import concepts"
	exit 1;
fi

start=`date +%s`
python manage.py import_mappings_to_source --source $SOURCE --token PERF_TEST_TOKEN --inline-indexing true perf_data/ciel_20160711_mappings_2k.json
end=`date +%s`
runtime=$((end-start))
echo "Took ${runtime} sec to diff import mappings"
if [ $runtime -ge 120 ];
then
	echo >&2 "It has taken longer to re-import mappings"
	exit 1;
fi
