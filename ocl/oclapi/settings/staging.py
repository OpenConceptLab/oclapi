from oclapi.settings.common import *

class Staging(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS

    SECRET_KEY = values.SecretValue(environ_name='SECRET_KEY', environ_prefix='')

    BASE_URL = 'https://api.staging.openconceptlab.org'

    USE_X_FORWARDED_HOST = True

    # used to push logs to sentry.io/openconceptlab
    SENTRY_DSN_KEY = values.SecretValue(environ_name="SENTRY_DSN_KEY", environ_prefix="")
    RAVEN_CONFIG = {
        'dsn': SENTRY_DSN_KEY,
    }