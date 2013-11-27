from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.mixins import ConceptContainerMixin, ConceptContainerVersionMixin
from oclapi.models import SubResourceBaseModel, ResourceVersionModel
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


class Source(SubResourceBaseModel, ConceptContainerMixin):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    source_type = models.TextField(choices=SRC_TYPE_CHOICES, default=DEFAULT_SRC_TYPE, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    @classmethod
    def resource_type(cls):
        return SOURCE_TYPE

    @classmethod
    def get_version_model(cls):
        return SourceVersion

    @staticmethod
    def get_url_kwarg():
        return 'source'


class SourceVersion(ResourceVersionModel, ConceptContainerVersionMixin):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    source_type = models.TextField(choices=SRC_TYPE_CHOICES, default=DEFAULT_SRC_TYPE, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    concepts = ListField()

    def update_concept_version(self, concept_version):
        previous_version = concept_version.previous_version
        if previous_version and previous_version.id in self.concepts:
            index = self.concepts.index(previous_version.id)
            self.concepts[index] = concept_version.id
        else:
            self.concepts.append(concept_version.id)

    @classmethod
    def for_base_object(cls, source, label, previous_version=None, parent_version=None):
        return SourceVersion(
            mnemonic=label,
            name=source.name,
            full_name=source.full_name,
            source_type=source.source_type,
            public_access=source.public_access,
            default_locale=source.default_locale,
            supported_locales=source.supported_locales,
            website=source.website,
            description=source.description,
            versioned_object_id=source.id,
            versioned_object_type=ContentType.objects.get_for_model(Source),
            released=False,
            previous_version=previous_version,
            parent_version=parent_version
        )


admin.site.register(Source)
admin.site.register(SourceVersion)