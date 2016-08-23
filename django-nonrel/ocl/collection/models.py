from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField, EmbeddedModelField
from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel
from oclapi.utils import reverse_resource
from concepts.models import Concept
from mappings.models import Mapping


COLLECTION_TYPE = 'Collection'
HEAD = 'HEAD'

class Collection(ConceptContainerModel):
    collection_type = models.TextField(blank=True)

    @property
    def concepts_url(self):
        return reverse_resource(self, 'collection-concept-list')

    @property
    def versions_url(self):
        return reverse_resource(self, 'collectionversion-list')

    @property
    def resource_type(self):
        return COLLECTION_TYPE

    @classmethod
    def get_version_model(cls):
        return CollectionVersion

    @staticmethod
    def get_url_kwarg():
        return 'collection'

COLLECTION_VERSION_TYPE = "Collection Version"


class CollectionReference(models.Model):
    expression = models.TextField()
    concepts = ListField()
    mappings = ListField()

    def clean(self):
        if not Concept.objects.filter(uri=self.expression):
            if not Mapping.objects.filter(uri=self.expression):
                raise ValidationError('Expression specified is not valid.')


class CollectionVersion(ConceptContainerVersionModel):
    collection_type = models.TextField(blank=True)
    concept_references = ListField()
    references = ListField(EmbeddedModelField("CollectionReference"))

    def add_expression(self, expression):
        a_reference = CollectionReference(expression=expression)
        a_reference.full_clean()
        self.references.append(a_reference)

    def seed_concepts(self):
        seed_concepts_from = self.previous_version or self.parent_version
        if seed_concepts_from:
            self.concept_references = list(seed_concepts_from.concept_references)

    def head_sibling(self):
        return CollectionVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.versioned_object_id)

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()
        col_expression = kwargs.pop('expression', False)
        if col_expression:
            try:
                obj.add_expression(col_expression)
            except ValidationError as err:
                errors['detail'] = ', '.join(err.messages)
                return errors
        return super(CollectionVersion, cls).persist_changes(obj, **kwargs)

    @classmethod
    def get_head(self, id):
        return CollectionVersion.objects.get(mnemonic=HEAD, versioned_object_id=id)

    @property
    def resource_type(self):
        return COLLECTION_VERSION_TYPE

    @classmethod
    def for_base_object(cls, collection, label, previous_version=None, parent_version=None, released=False):
        if not Collection == type(collection):
            raise ValidationError("source must be of type 'Source'")
        if not collection.id:
            raise ValidationError("source must have an Object ID.")
        if label == 'INITIAL':
            label = HEAD
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
            parent_version=parent_version,
            created_by=collection.created_by,
            updated_by=collection.updated_by,
            external_id=collection.external_id,
        )


admin.site.register(Collection)
admin.site.register(CollectionVersion)

@receiver(post_save)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return False
    for collection in Collection.objects.filter(parent_id=instance.id, parent_type=ContentType.objects.get_for_model(sender)):
        if instance.is_active != collection.is_active:
            collection.undelete() if instance.is_active else collection.soft_delete()
