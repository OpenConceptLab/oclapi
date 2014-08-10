from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField
from concepts.models import ConceptReference
from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel
from oclapi.utils import reverse_resource

COLLECTION_TYPE = 'Collection'


class Collection(ConceptContainerModel):
    collection_type = models.TextField(blank=True)

    @property
    def versions_url(self):
        return reverse_resource(self, 'collectionversion-list')

    @property
    def concepts_url(self):
        return reverse_resource(self, 'concept-create')

    @property
    def resource_type(self):
        return COLLECTION_TYPE

    @property
    def num_concepts(self):
        return ConceptReference.objects.filter(parent_id=self.id).count()

    @classmethod
    def get_version_model(cls):
        return CollectionVersion

    @staticmethod
    def get_url_kwarg():
        return 'collection'

COLLECTION_VERSION_TYPE = "Collection Version"


class CollectionVersion(ConceptContainerVersionModel):
    collection_type = models.TextField(blank=True)
    concept_references = ListField()

    def seed_concepts(self):
        seed_concepts_from = self.previous_version or self.parent_version
        if seed_concepts_from:
            self.concept_references = list(seed_concepts_from.concept_references)

    @property
    def resource_type(self):
        return COLLECTION_VERSION_TYPE

    @classmethod
    def for_base_object(cls, collection, label, previous_version=None, parent_version=None, released=False):
        if not Collection == type(collection):
            raise ValidationError("source must be of type 'Source'")
        if not collection.id:
            raise ValidationError("source must have an Object ID.")
        return CollectionVersion(
            mnemonic=label,
            name=collection.name,
            full_name=collection.full_name,
            collection_type=collection.collection_type,
            public_access=collection.public_access,
            default_locale=collection.default_locale,
            supported_locales=collection.supported_locales,
            website=collection.website,
            description=collection.description,
            versioned_object_id=collection.id,
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            released=released,
            previous_version=previous_version,
            parent_version=parent_version
        )


admin.site.register(Collection)
admin.site.register(CollectionVersion)

@receiver(post_save, sender=User)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if instance.is_active:
        for collection in Collection.objects.filter(owner=instance):
            collection.undelete()
    else:
        for collection in Collection.objects.filter(owner=instance):
            collection.soft_delete()
