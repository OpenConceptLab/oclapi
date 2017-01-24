#!/bin/bash

ROOT_PWD=Root123

echo "from django.contrib.auth.models import User; from users.models import UserProfile; from orgs.models import Organization; UserProfile.objects.create(user=User.objects.create_superuser('root', 'root@example.com', $ROOT_PWD), organizations=map(lambda o: o.id, Organization.objects.filter(created_by='root')), mnemonic='root')" | python manage.py shell
echo "Settings for: $1"
echo "Configurations for: $2"

SETTINGS=$1
CONFIG=$2
export AWS_ACCESS_KEY_ID=$3
export AWS_SECRET_ACCESS_KEY=$4
export AWS_STORAGE_BUCKET_NAME=$5
if [ -z $1 ]; then export SETTINGS=local; export CONFIG=Local; fi;

python manage.py syncdb --noinput --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"
python manage.py runserver 0.0.0.0:8000 --settings="oclapi.settings.$SETTINGS" --configuration="$CONFIG"