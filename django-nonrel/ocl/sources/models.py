from django.contrib import admin
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import SubResourceBaseModel, BaseModel
from settings import DEFAULT_LOCALE

SOURCE_TYPE = 'Source'

DICTIONARY_SRC_TYPE = 'dictionary'
DEFAULT_SRC_TYPE = DICTIONARY_SRC_TYPE
SRC_TYPE_CHOICES = (('dictionary', 'Dictionary'),
                    ('reference', 'Reference'),
                    ('externalDictionary', 'External Dictionary'))

VIEW_ACCESS_TYPE = 'View'
EDIT_ACCESS_TYPE = 'Edit'
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

    @property
    def num_versions(self):
        return SourceVersion.objects.filter(source=self).count()

    @classmethod
    def resource_type(self):
        return SOURCE_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'source'


class SourceVersion(BaseModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    source_type = models.TextField(choices=SRC_TYPE_CHOICES, default=DEFAULT_SRC_TYPE, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    source = models.ForeignKey(Source, related_name='versions')
    label = models.TextField(null=True, blank=True)
    released = models.BooleanField(default=False, blank=True)
    previous_version = models.OneToOneField('self', related_name='next_version', null=True, blank=True)
    parent_version = models.OneToOneField('self', related_name='child_version', null=True, blank=True)
    concepts = ListField()

    @classmethod
    def for_source(cls, source, label, previous_version=None, parent_version=None):
        return SourceVersion(
            mnemonic="%s__%s" % (source.mnemonic, label),
            name=source.name,
            full_name=source.full_name,
            source_type=source.source_type,
            public_access=source.public_access,
            default_locale=source.default_locale,
            supported_locales=source.supported_locales,
            website=source.website,
            description=source.description,
            source=source,
            label=label,
            released=False,
            previous_version=previous_version,
            parent_version=parent_version
        )


admin.site.register(Source)
admin.site.register(SourceVersion)