from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField
from oclapi.models import SubResourceBaseModel, ResourceVersionModel
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

    @classmethod
    def resource_type(cls):
        return COLLECTION_TYPE

    @classmethod
    def get_version_model(cls):
        return CollectionVersion

    @staticmethod
    def get_url_kwarg():
        return 'collection'

    @property
    def num_versions(self):
        return self.get_version_model().objects.filter(versioned_object_id=self.id).count()

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource')
        user = kwargs.pop('owner')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if cls.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            errors['mnemonic'] = '%s with mnemonic %s already exists for parent resource %s.' % (cls, mnemonic, parent_resource.mnemonic)
            return errors
        obj.parent = parent_resource
        obj.owner = user
        persisted = False
        version = None
        try:
            obj.save(**kwargs)
            version_model = cls.get_version_model()
            version = version_model.for_base_object(obj, 'INITIAL')
            version.released = True
            version.save()
            version.mnemonic = version.id
            version.save()
            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = 'An error occurred while trying to persist new source.'
                if version:
                    version.delete()
                obj.delete()
        return errors

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        matching_sources = cls.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic)
        if matching_sources.exists():
            if matching_sources[0] != obj:
                errors['mnemonic'] = '%s with mnemonic %s already exists for parent resource %s.' % (cls, mnemonic, parent_resource.mnemonic)
                return errors
        obj.save(**kwargs)
        return errors


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

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        versioned_object = kwargs.get('versioned_object', None)
        if versioned_object is None:
            errors['non_field_errors'] = ['Must specify a versioned object.']
            return errors
        if cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj.mnemonic).exists():
            errors['mnemonic'] = ["Version with mnemonic %s already exists for source %s." % (obj.mnemonic, versioned_object.mnemonic)]
            return errors
        kwargs['seed_concepts'] = True
        return cls.persist_changes(obj, **kwargs)

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()
        versioned_object = kwargs.pop('versioned_object')
        if versioned_object is None:
            errors['non_field_errors'] = ['Must specify a versioned object.']
            return errors
        if obj._previous_version_mnemonic:
            previous_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._previous_version_mnemonic)
            if not previous_version_queryset.exists():
                errors['previousVersion'] = ["Previous version %s does not exist." % obj._previous_version_mnemonic]
            elif obj.mnemonic == obj._previous_version_mnemonic:
                errors['previousVersion'] = ["Previous version cannot be the same as current version."]
            else:
                obj.previous_version = previous_version_queryset[0]
                del obj._previous_version_mnemonic
        if obj._parent_version_mnemonic:
            parent_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._parent_version_mnemonic)
            if not parent_version_queryset.exists():
                errors['parentVersion'] = ["Parent version %s does not exist." % obj._parent_version_mnemonic]
            elif obj.mnemonic == obj._parent_version_mnemonic:
                errors['parentVersion'] = ["Parent version cannot be the same as current version."]
            else:
                obj.parent_version = parent_version_queryset[0]
                del obj._parent_version_mnemonic
        if errors:
            return errors
        seed_concepts = kwargs.pop('seed_concepts', False)
        if seed_concepts:
            seed_concepts_from = obj.previous_version or obj.parent_version
            if seed_concepts_from:
                obj.concepts = list(seed_concepts_from.concepts)
        obj.versioned_object = versioned_object
        updated = False
        try:
            obj.save(**kwargs)
            updated = True
        finally:
            if not updated:
                errors['non_field_errors'] = ["Encountered an error while updating version."]
        return errors


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
