#!/bin/bash

SETTINGS=$1
CONFIG=$2
export AWS_ACCESS_KEY_ID=$3
export AWS_SECRET_ACCESS_KEY=$4
export AWS_STORAGE_BUCKET_NAME=$5
ROOT_PWD=$6

if [ -z $1 ]; then export SETTINGS=local; export CONFIG=Local; fi;
if [ -z $6 ]; then ROOT_PWD=Root123; fi;

echo "from django.contrib.auth.models import User; from users.models import UserProfile; from orgs.models import Organization; UserProfile.objects.create(user=User.objects.create_superuser('root', 'root@example.com', '$ROOT_PWD'), organizations=map(lambda o: o.id, Organization.objects.filter(created_by='root')), mnemonic='root')" | python manage.py shell
echo "Settings for: $SETTINGS"
echo "Configurations for: $CONFIG"

python manage.py syncdb --noinput --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"

echo "Importing Lookup Values"
python manage.py import_lookup_values

echo "Starting the server"
python manage.py runserver 0.0.0.0:8000 --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"
