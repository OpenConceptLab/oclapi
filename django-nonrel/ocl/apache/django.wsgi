import os
import sys

path = '/opt/deploy/django/ocl'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'ocl.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
