#!/bin/bash

echo "from django.contrib.auth.models import User; user = User.objects.create_superuser('root', 'root@example.com', 'Root123') if (User.objects.filter(username='root').count() < 1) else None" | python manage.py shell
echo "Settings for: $1"
echo "Configurations for: $2"

SETTINGS=$1
CONFIG=$2

if [ -z $1 ]; then export SETTINGS=local; export CONFIG=Local; fi;

python manage.py syncdb --noinput --settings="oclapi.settings.$CONFIG" --configuration="$CONFIG"
python manage.py runserver 0.0.0.0:8000 --settings="oclapi.settings.$CONFIG" --configuration="$CONFIG"
