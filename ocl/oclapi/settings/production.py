from oclapi.settings.common import *

class Production(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS

    SECRET_KEY = values.SecretValue(environ_name='SECRET_KEY', environ_prefix='')

    BASE_URL = 'https://api.openconceptlab.org'

    USE_X_FORWARDED_HOST = True