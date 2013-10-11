from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import BaseModel
from sources.models import Source

ORG_OBJECT_TYPE = 'Organization'


class Organization(BaseModel):
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)
    members = ListField()
    sources = ListField()
    group = models.OneToOneField(Group)

    def __unicode__(self):
        return self.name

    @classmethod
    def resource_type(cls):
        return ORG_OBJECT_TYPE

    @property
    def num_members(self):
        return len(self.members)

    @property
    def public_sources(self):
        return Source.objects.filter(parent_id=self.id).count()

    @staticmethod
    def get_url_kwarg():
        return 'org'


admin.site.register(Organization)
