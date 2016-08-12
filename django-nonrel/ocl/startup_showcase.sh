#!/bin/bash
echo "right place"
echo "from django.contrib.auth.models import User; user = User.objects.create_superuser('root', 'root@example.com', 'Root123') if (User.objects.filter(username='root').count() < 1) else None" | python manage.py shell

python manage.py syncdb --noinput --settings='oclapi.settings.showcase' --configuration='Showcase'
python manage.py runserver 0.0.0.0:8000 --settings='oclapi.settings.showcase' --configuration='Showcase'