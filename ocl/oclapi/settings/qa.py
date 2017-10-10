from oclapi.settings.common import *

class Qa(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS

    SECRET_KEY = values.SecretValue(environ_name='SECRET_KEY', environ_prefix='')

    BASE_URL = 'https://api.qa.openconceptlab.org'

    USE_X_FORWARDED_HOST = True