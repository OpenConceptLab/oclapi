#!/bin/bash

echo "from django.contrib.auth.models import User; user = User.objects.create_superuser('root', 'root@example.com', 'Root123') if (User.objects.filter(username='root').count() < 1) else None" | python manage.py shell
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
