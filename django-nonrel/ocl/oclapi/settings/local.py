from oclapi.settings.common import *

class Local(Common):

    # DEBUG = False
    EMAIL_HOST = "10.133.22.210"
    EMAIL_PORT = 1025
    EMAIL_BACKEND = values.Value('django.core.mail.backends.console.EmailBackend')

    INSTALLED_APPS = Common.INSTALLED_APPS

    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_engine',
            'HOST': '10.133.22.210',
            'NAME': 'ocl',
        }
    }

    BROKER_URL = 'mongodb://10.133.22.210:27017/ocl'
    INTERNAL_IPS = ('10.133.22.210',)
