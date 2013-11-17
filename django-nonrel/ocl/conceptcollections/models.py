from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.mixins import ConceptContainerMixin, ConceptContainerVersionMixin
from oclapi.models import SubResourceBaseModel, ResourceVersionModel
from settings import DEFAULT_LOCALE

COLLECTION_TYPE = 'Collection'

VIEW_ACCESS_TYPE = 'View'
EDIT_ACCESS_TYPE = 'Edit'
DEFAULT_ACCESS_TYPE = VIEW_ACCESS_TYPE
ACCESS_TYPE_CHOICES = (('View', 'View'),
                       ('Edit', 'Edit'),
                       ('None', 'None'))


class Collection(SubResourceBaseModel, ConceptContainerMixin):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    @classmethod
    def resource_type(cls):
        return COLLECTION_TYPE

    @classmethod
    def get_version_model(cls):
        return CollectionVersion

    @staticmethod
    def get_url_kwarg():
        return 'collection'


class CollectionVersion(ResourceVersionModel, ConceptContainerVersionMixin):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    concepts = ListField()

    @classmethod
    def for_base_object(cls, collection, label, previous_version=None, parent_version=None):
        return CollectionVersion(
            mnemonic=label,
            name=collection.name,
            full_name=collection.full_name,
            public_access=collection.public_access,
            default_locale=collection.default_locale,
            supported_locales=collection.supported_locales,
            website=collection.website,
            description=collection.description,
            versioned_object_id=collection.id,
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            released=False,
            previous_version=previous_version,
            parent_version=parent_version
        )


admin.site.register(Collection)
admin.site.register(CollectionVersion)