from oclapi.settings.common import *
from configurations import values


class Local(Common):
    BASE_URL = 'http://localhost:8000'

    SECRET_KEY = values.Value(environ_name='SECRET_KEY', environ_prefix='', default='s3owRP0sLI2opDDI6qIgG3iD57')

    # DEBUG = False
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 1025
    EMAIL_BACKEND = values.Value('django.core.mail.backends.console.EmailBackend')

    INSTALLED_APPS = Common.INSTALLED_APPS
    INTERNAL_IPS = ('localhost',)

    DEBUG = True
    TEMPLATE_DEBUG = DEBUG

class Dev(Local):
    """
    Settings for unit testing
    """
    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'

class Test(Local):
    """
    Settings for unit testing
    """
    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_engine',
            'HOST': 'localhost',
            'NAME': 'test',
        }
    }
    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'


class IntegrationTest(Common):
    """
    Settings for unit testing
    """
    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_engine',
            'HOST': 'localhost',
            'NAME': 'ocl',
        }
    }

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'oclapi.search_backends.OCLSolrEngine',
            'URL': 'http://localhost:8983/solr/collection1'
            # ...or for multicore...
            # 'URL': 'http://127.0.0.1:8983/solr/mysite',
        },
    }
    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'

    BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    INSTALLED_APPS = Common.INSTALLED_APPS
