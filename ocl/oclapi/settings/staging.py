from oclapi.settings.common iUPDATE: I've scheduled retrieval of our oldest backup from May (it will take a couple of hours), because newer backups from November did not include packages.mport *

class Staging(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS

    SECRET_KEY = values.SecretValue(environ_name='SECRET_KEY', environ_prefix='')

    BASE_URL = 'https://api.staging.openconceptlab.org'

    USE_X_FORWARDED_HOST = True

    # used to push logs to sentry.io/openconceptlab
    RAVEN_CONFIG = {
        'dsn': os.environ.get('SENTRY_DSN_KEY', ''),
    }