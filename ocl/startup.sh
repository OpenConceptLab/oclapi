#!/bin/bash

if [ $SSH ] 
then 
sudo service ssh start 
fi

if [ ! -z "$WAIT_FOR" ] 
then
for WAIT in ${WAIT_FOR//,/ } 
do
    ./wait-for-it.sh $WAIT
done
fi

if [ -z $ENVIRONMENT ]
then 
export SETTINGS=local
export CONFIG=Local
else
export SETTINGS=$ENVIRONMENT
export CONFIG=${ENVIRONMENT^}
fi

echo "Settings for: $SETTINGS"
echo "Configurations for: $CONFIG"

python manage.py syncdb --noinput --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

echo "Setting up superuser"

if [ -z $ROOT_PASSWORD ]; then ROOT_PASSWORD=Root123; fi;

python manage.py create_tokens --password="$ROOT_PASSWORD" --token="$OCL_API_TOKEN" --create

echo "Run before startup"
python manage.py run_before_startup --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

echo "Importing Lookup Values"
python manage.py import_lookup_values --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

echo "Run data integrity checks"
python manage.py run_data_integrity_checks --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

if [ "$IMPORT_DEMO_DATA" = true ]
then
echo "Importing Demo Data"
python manage.py import_demo_data --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"
fi

echo "Starting the server"
python manage.py runserver 0.0.0.0:8000 --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG" --insecure
