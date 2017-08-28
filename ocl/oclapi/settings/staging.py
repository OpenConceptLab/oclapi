from oclapi.settings.common import *

class Staging(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS
    DEBUG = False
    TEMPLATE_DEBUG = DEBUG