# Django settings for the ocl project.
# We need to switch to use django-configuration soon.
#
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Jon Payne', 'paynejd@gmail.com'),
    ('PK Shiu', 'pk@pkshiu.com'),
)

MANAGERS = ADMINS

# Set this to something else for personal development
# This value is used in several places.
# e.g. DATABASE_HOST = 'api.dev.openconceptlab.org'
DATABASE_HOST = 'localhost'

DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_engine',
        'HOST': DATABASE_HOST,
        'NAME': 'ocl',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.3/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True
DEFAULT_LOCALE = 'en'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''
# In the deployment environment, comment out the above line, and uncomment the one below
#STATIC_ROOT = '/usr/local/wsgi/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '+p+lx2*o3ywq+z)%f7929b6)93)^mcc9-0eu9ynq77gc+pe=ck'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    # Core OCL app
    'oclapi',
    # Third-party apps:
    'djangotoolbox',
    'django_mongodb_engine',
    'rest_framework',
    'rest_framework.authtoken',
    'haystack',
    # Project-specific apps:
    'users',
    'orgs',
    'sources',
    'concepts',
    'collection',
    'mappings',
)

# Django Rest Framework configuration
REST_FRAMEWORK = {
    # Default to token-based authentication; fall back on session-based
    # A user gets a unique token upon account creation (residing in the authtoken_token data store).
    # To pass an authentication token along with your request, include the following header:
    # Authorization: Token [TOKEN_VALUE]
    # e.g.
    # Authorization: Token ad73f481096c3b6202bce395820199
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'oclapi.renderers.ZippedJSONRenderer',
    ),
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'oclapi.negotiation.OptionallyCompressContentNegotiation',
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    'DEFAULT_PAGINATION_SERIALIZER_CLASS':
        'oclapi.serializers.HeaderPaginationSerializer',
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        #'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        'rest_framework.permissions.IsAuthenticated',
    ],
    'PAGINATE_BY': 10,             # Default to 10
    'PAGINATE_BY_PARAM': 'limit',  # Allow client to override, using `?limit=xxx`.
    'MAX_PAGINATE_BY': 100         # Maximum limit allowed when using `?limit=xxx`.
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'oclapi.search_backends.OCLSolrEngine',
        'URL': 'http://127.0.0.1:8983/solr'
        # ...or for multicore...
        # 'URL': 'http://127.0.0.1:8983/solr/mysite',
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

# Celery settings
# BROKER_URL = 'django://'
BROKER_URL = 'mongodb://%s:27017/ocl' % DATABASE_HOST
CELERY_RESULT_BACKEND = "mongodb"
# Set these in your postactivate hook if you use virtualenvwrapper
AWS_ACCESS_KEY_ID=os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY=os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME=os.environ['AWS_STORAGE_BUCKET_NAME']


# Model that stores auxiliary user profile attributes.
# A user must have a profile in order to access the system.
# (A profile is created automatically for any user created using the 'POST /users' endpoint.)
AUTH_PROFILE_MODULE = 'users.UserProfile'
