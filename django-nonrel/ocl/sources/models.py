from django.contrib import admin
from oclapi.models import NonrelMixin, RestrictedBaseModel


class Source(RestrictedBaseModel, NonrelMixin):
    def __unicode__(self):
        return self.mnemonic

admin.site.register(Source)