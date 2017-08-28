from oclapi.settings.common import *

class Production(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS
    DEBUG = False
    TEMPLATE_DEBUG = DEBUG