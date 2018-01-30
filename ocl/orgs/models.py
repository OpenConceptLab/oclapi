from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from djangotoolbox.fields import ListField
from collection.models import Collection
from oclapi.models import BaseResourceModel, ACCESS_TYPE_NONE
from sources.models import Source
from oclapi.utils import lazyproperty

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

    @lazyproperty
    def public_collections(self):
        return Collection.objects.filter(~Q(public_access=ACCESS_TYPE_NONE), parent_id=self.id).count()

    @lazyproperty
    def public_sources(self):
        return Source.objects.filter(~Q(public_access=ACCESS_TYPE_NONE), parent_id=self.id).count()

    @property
    def members_url(self):
        return reverse('organization-members', kwargs={'org': self.mnemonic})

    @property
    def sources_url(self):
        return reverse('source-list', kwargs={'org': self.mnemonic})

    @property
    def collections_url(self):
        return reverse('collection-list', kwargs={'org': self.mnemonic})

    @property
    def num_stars(self):
        return 0

    @staticmethod
    def get_url_kwarg():
        return 'org'


admin.site.register(Organization)
