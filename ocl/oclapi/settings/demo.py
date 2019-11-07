from oclapi.settings.common import *

class Demo(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS

    SECRET_KEY = values.SecretValue(environ_name='SECRET_KEY', environ_prefix='')

    BASE_URL = 'https://api.demo.openconceptlab.org'

    USE_X_FORWARDED_HOST = True

    # used to push logs to sentry.io/openconceptlab
    RAVEN_CONFIG = {
        'dsn': os.environ.get('SENTRY_DSN_KEY', ''),
    }