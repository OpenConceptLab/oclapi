from django.contrib import admin
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import SubResourceBaseModel, BaseModel
from orgs.models import Organization
from settings import DEFAULT_LOCALE

SOURCE_TYPE = 'Source'

DICTIONARY_SRC_TYPE = 'dictionary'
DEFAULT_SRC_TYPE = DICTIONARY_SRC_TYPE
SRC_TYPE_CHOICES = (('dictionary', 'Dictionary'),
                    ('reference', 'Reference'),
                    ('externalDictionary', 'External Dictionary'))

VIEW_ACCESS_TYPE = 'View'
DEFAULT_ACCESS_TYPE = VIEW_ACCESS_TYPE
ACCESS_TYPE_CHOICES = (('View', 'View'),
                       ('Edit', 'Edit'),
                       ('None', 'None'))


class Source(SubResourceBaseModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    source_type = models.TextField(choices=SRC_TYPE_CHOICES, default=DEFAULT_SRC_TYPE, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    belongs_to_organization = models.ForeignKey(Organization, null=True, blank=True)

    @property
    def type(self):
        return SOURCE_TYPE


class SourceVersion(BaseModel):
    source = models.ForeignKey(Source)
    description = models.TextField(null=True, blank=True)
    released = models.BooleanField(default=False, blank=True)
    previous_version = models.OneToOneField('self', related_name='next_version', null=True, blank=True)
    parent_version = models.ManyToManyField('self', related_name='child_version', null=True, blank=True)
    concepts = ListField()


admin.site.register(Source)
admin.site.register(SourceVersion)