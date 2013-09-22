from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import BaseModel

ORG_OBJECT_TYPE = 'Organization'


class Organization(BaseModel):
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    members = ListField()
    group = models.OneToOneField(Group)

    def __unicode__(self):
        return self.name

    @property
    def type(self):
        return ORG_OBJECT_TYPE


admin.site.register(Organization)
