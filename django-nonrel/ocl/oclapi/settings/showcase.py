from oclapi.settings.common import *

class Showcase(Common):

    DEBUG = False
    INSTALLED_APPS = Common.INSTALLED_APPS

    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_engine',
            'HOST': '192.241.144.33',
            'NAME': 'ocl',
        }
    }

    BROKER_URL = 'mongodb://192.241.144.33:27017/ocl'
    INTERNAL_IPS = ('192.241.144.33',)