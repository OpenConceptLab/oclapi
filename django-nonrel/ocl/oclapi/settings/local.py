from oclapi.settings.common import *

class Local(Common):

    # DEBUG = False
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 1025
    EMAIL_BACKEND = values.Value('django.core.mail.backends.console.EmailBackend')

    INSTALLED_APPS = Common.INSTALLED_APPS
    INTERNAL_IPS = ('localhost',)

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

