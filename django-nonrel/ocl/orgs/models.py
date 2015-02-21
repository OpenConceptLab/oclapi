from django.contrib import admin
from django.db import models
from django.db.models import Q
from djangotoolbox.fields import ListField
from collection.models import Collection
from oclapi.models import BaseResourceModel, ACCESS_TYPE_NONE
from sources.models import Source

ORG_OBJECT_TYPE = 'Organization'


class Organization(BaseResourceModel):
    name = models.TextField()
    company = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    members = ListField()

    def __unicode__(self):
        return self.mnemonic

    @classmethod
    def resource_type(cls):
        return ORG_OBJECT_TYPE

    @property
    def num_members(self):
        return len(self.members)

    @property
    def public_collections(self):
        return Collection.objects.filter(~Q(public_access=ACCESS_TYPE_NONE), parent_id=self.id).count()

    @property
    def public_sources(self):
        return Source.objects.filter(~Q(public_access=ACCESS_TYPE_NONE), parent_id=self.id).count()

    @property
    def num_stars(self):
        return 0

    @staticmethod
    def get_url_kwarg():
        return 'org'


admin.site.register(Organization)
