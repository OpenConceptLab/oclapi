from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import SubResourceBaseModel, ResourceVersionModel, VERSION_TYPE
from settings import DEFAULT_LOCALE

COLLECTION_TYPE = 'Collection'

VIEW_ACCESS_TYPE = 'View'
EDIT_ACCESS_TYPE = 'Edit'
DEFAULT_ACCESS_TYPE = VIEW_ACCESS_TYPE
ACCESS_TYPE_CHOICES = (('View', 'View'),
                       ('Edit', 'Edit'),
                       ('None', 'None'))


class Collection(SubResourceBaseModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    @property
    def num_versions(self):
        return CollectionVersion.objects.filter(versioned_object_id=self.id).count()

    @classmethod
    def resource_type(cls):
        return COLLECTION_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'collection'


class CollectionVersion(ResourceVersionModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    public_access = models.TextField(choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    concepts = ListField()

    @classmethod
    def for_collection(cls, collection, label, previous_version=None, parent_version=None):
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

    @classmethod
    def resource_type(cls):
        return VERSION_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'version'

admin.site.register(Collection)
admin.site.register(CollectionVersion)