import collections
import logging
import re
import ast

from bson import ObjectId
from celery.result import AsyncResult
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django_mongodb_engine.contrib import MongoDBManager
from djangotoolbox.fields import DictField, ListField, SetField
from rest_framework.authtoken.models import Token

from oclapi.utils import reverse_resource, reverse_resource_version
from oclapi.settings.common import Common
from django.db.models import get_model

logger = logging.getLogger('oclapi')

HEAD = 'HEAD'

NAMESPACE_PATTERN = '[a-zA-Z0-9\-\.]+'
CONCEPT_ID_PATTERN = '[a-zA-Z0-9\-\.\_]+'
NAMESPACE_REGEX = re.compile(r'^' + NAMESPACE_PATTERN + '$')
CONCEPT_ID_REGEX = re.compile(r'^' + CONCEPT_ID_PATTERN + '$')

ACCESS_TYPE_VIEW = 'View'
ACCESS_TYPE_EDIT = 'Edit'
ACCESS_TYPE_NONE = 'None'
DEFAULT_ACCESS_TYPE = ACCESS_TYPE_VIEW
ACCESS_TYPE_CHOICES = ((ACCESS_TYPE_VIEW, 'View'),
                       (ACCESS_TYPE_EDIT, 'Edit'),
                       (ACCESS_TYPE_NONE, 'None'))


class BaseModel(models.Model):
    """
    Base model from which all resources inherit.  Contains timestamps and is_active field for logical deletion.
    """
    public_access = models.CharField(max_length=16, choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.TextField()
    updated_by = models.TextField()
    is_active = models.BooleanField(default=True)
    is_being_saved = False
    extras = DictField(null=True, blank=True)
    extras_have_been_encoded = False
    extras_have_been_decoded = False
    uri = models.TextField(null=True, blank=True)

    objects = MongoDBManager()

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.is_being_saved = True
        self.encode_extras()
        super(BaseModel, self).save(force_insert, force_update, using, update_fields)
        self.is_being_saved = False


    def __setattr__(self, attrname, val):
        if("extras" == attrname and val is not None and self.is_being_saved == False and self.extras_have_been_decoded == False):
            self.decode_extras(val)
            self.extras_have_been_decoded = True
        super(BaseModel, self).__setattr__(attrname, val)

    @property
    def url(self):
        return self.uri or reverse_resource(self, self.view_name)

    @property
    def view_name(self):
        return self.get_default_view_name()

    @property
    def _default_view_name(self):
        return '%(model_name)s-detail'

    def soft_delete(self):
        if self.is_active:
            self.is_active = False
            self.save()

    def undelete(self):
        if not self.is_active:
            self.is_active = True
            self.save()

    def get_default_view_name(self):
        model = self.__class__
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs

    def encode_extras(self):
        if self.extras is not None and self.extras_have_been_encoded == False:
            self.encode_extras_recursively(self.extras)
            self.extras_have_been_encoded = True
        return

    def encode_extras_recursively(self, extras):
        if isinstance(extras, collections.Mapping):
            for old_key in extras:
                key = old_key
                key = key.replace('%', '%25')
                key = key.replace('.','%2E')
                value = extras.get(old_key)
                self.encode_extras_recursively(value)
                if key is not old_key:
                    extras.pop(old_key)
                    extras[key] = value
        elif isinstance(extras, list):
            for item in extras:
                self.encode_extras_recursively(item)

    def decode_extras(self, extras):
        if isinstance(extras, collections.Mapping):
            for old_key in extras:
                key = old_key
                key = key.replace('%25', '%')
                key = key.replace('%2E', '.')
                value = extras.get(old_key)
                self.decode_extras(value)
                if key is not old_key:
                    extras.pop(old_key)
                    extras[key] = value
        elif isinstance(extras, list):
            for item in extras:
                self.decode_extras(item)


class BaseResourceModel(BaseModel):
    """
    A base resource has a mnemonic that is unique across all objects of its type.
    A base resource may contain sub-resources.
    (An Organization is a base resource, but a Concept is not.)
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)], unique=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.mnemonic


class SubResourceBaseModel(BaseModel):
    """
    A sub-resource is an object that exists within the scope of its parent resource.
    Its mnemonic is unique within the scope of its parent resource.
    (A Source is a sub-resource, but an Organization is not.)
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    parent_type = models.ForeignKey(ContentType, db_index=False)
    parent_id = models.TextField()
    parent = generic.GenericForeignKey('parent_type', 'parent_id')

    class Meta:
        abstract = True
        unique_together = ('mnemonic', 'parent_id')

    def __unicode__(self):
        return self.mnemonic

    @property
    def parent_url(self):
        return self.parent.url

    @property
    def parent_resource(self):
        return self.parent.mnemonic

    @property
    def parent_resource_type(self):
        return self.parent.resource_type


class ConceptBaseModel(BaseModel):
    """
    Similar to SubResourceBaseModel, with a different mnemonic validator
    It pains me to duplicate code in this way, but I cannot find a more
        elegant way to do this.
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=CONCEPT_ID_REGEX)])
    parent_type = models.ForeignKey(ContentType, db_index=False)
    parent_id = models.TextField()
    parent = generic.GenericForeignKey('parent_type', 'parent_id')

    class Meta:
        abstract = True
        unique_together = ('mnemonic', 'parent_id')

    def __unicode__(self):
        return self.mnemonic

    @property
    def parent_url(self):
        return self.parent.url

    @property
    def parent_resource(self):
        return self.parent.mnemonic

    @property
    def parent_resource_type(self):
        return self.parent.resource_type


VERSION_TYPE = 'Version'


class ResourceVersionModel(BaseModel):
    """
    This model represents a version of a resource.  It has links to its base resource,
    as well as its parent and previous versions (if any).
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    versioned_object_id = models.TextField()
    versioned_object_type = models.ForeignKey(ContentType, db_index=False)
    versioned_object = generic.GenericForeignKey('versioned_object_type', 'versioned_object_id')
    released = models.BooleanField(default=False, blank=True)
    previous_version = models.ForeignKey('self', related_name='next', null=True, blank=True, db_index=False)
    parent_version = models.ForeignKey('self', related_name='child', null=True, blank=True, db_index=False)

    class Meta:
        abstract = True
        unique_together = ('mnemonic', 'versioned_object_id')

    def __unicode__(self):
        return self.mnemonic

    # TODO This prevents ValidationMixin from functioning correctly, we should reconsider necessity of this check
    # def clean(self):
    #     if self == self.parent_version:
    #         raise ValidationError('version cannot be its own parent')

    @property
    def url(self):
        return self.uri or reverse_resource_version(self, self.view_name)

    @property
    def previous_version_mnemonic(self):
        return self.previous_version.mnemonic if self.previous_version else None

    @property
    def previous_version_url(self):
        return self.previous_version.url if self.previous_version else None

    @property
    def parent_version_mnemonic(self):
        return self.parent_version.mnemonic if self.parent_version else None

    @property
    def parent_resource(self):
        return self.versioned_object.parent_resource

    @property
    def parent_resource_type(self):
        return self.versioned_object.parent_resource_type

    @property
    def parent_url(self):
        return self.versioned_object.parent_url

    def get_collections(self):
        collection_ids = self.get_collection_versions().values_list('versioned_object_id', flat=True)
        from collection.models import Collection
        return Collection.objects.filter(id__in=list(collection_ids))

    def get_collection_ids(self):
        return list(self.get_collections().values_list('id', flat=True))

    def get_collection_version_ids(self):
        return list(self.get_collection_versions().values_list('id', flat=True))

    @classmethod
    def get_latest_version_of(cls, versioned_object):
        versions = versioned_object.get_version_model().objects.filter(versioned_object_id=versioned_object.id, is_active=True).order_by('-created_at')
        return versions[0] if versions else None

    @classmethod
    def get_head_of(cls, versioned_object):
        try:
            version = versioned_object.get_version_model().objects.get(versioned_object_id=versioned_object.id, is_active=True, mnemonic=HEAD)
            return version
        except:
            return None


CUSTOM_VALIDATION_SCHEMA_OPENMRS = 'OpenMRS'
LOOKUP_CONCEPT_CLASSES = ['Concept Class', 'Datatype', 'NameType', 'DescriptionType', 'MapType', 'Locale']
LOOKUP_SOURCES = ['Classes', 'Datatypes', 'NameTypes', 'DescriptionTypes', 'MapTypes', 'Locales']

class ConceptContainerModel(SubResourceBaseModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    default_locale = models.TextField(default=Common.DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    external_id = models.TextField(null=True, blank=True)
    custom_validation_schema = models.TextField(blank=True, null=True)

    class Meta(SubResourceBaseModel.Meta):
        abstract = True

    @property
    def owner(self):
        return self.parent

    @property
    def owner_name(self):
        return unicode(self.owner)

    @property
    def owner_type(self):
        return self.owner.resource_type()

    @property
    def owner_url(self):
        owner = self.owner.get_profile() if isinstance(self.owner, User) else self.owner
        return owner.url

    @property
    def num_versions(self):
        return self.get_version_model().objects.filter(versioned_object_id=self.id).count()

    @property
    def num_stars(self):
        return 0

    @classmethod
    def persist_new(cls, obj, created_by, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource', None)
        if not parent_resource:
            errors['parent'] = 'Parent resource cannot be None.'
        user = created_by
        if not user:
            errors['created_by'] = 'Creator cannot be None.'
        if errors:
            return errors

        obj.parent = parent_resource
        obj.created_by = user
        obj.updated_by = user
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
        if errors:
            return errors

        persisted = False
        version = None
        try:
            obj.save(**kwargs)
            version_model = cls.get_version_model()
            label = 'INITIAL'
            version = version_model.for_base_object(obj, label)

            if version.mnemonic == label:
                version.save()
                version.mnemonic = version.id
            else:
                version.save()

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = "An error occurred while trying to persist new %s." % cls.__name__
                if version and version.id:
                    version.delete()
                obj.delete()
        return errors

    @classmethod
    def persist_changes(cls, obj, updated_by, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource', obj.parent)
        if not parent_resource:
            errors['parent'] = 'Source parent cannot be None.'

        if cls.validation_is_necessary(obj):
            failed_concept_validations = cls.validate_child_concepts(obj) or []
            if len(failed_concept_validations) > 0:
                errors.update({'failed_concept_validations': failed_concept_validations})

        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)

        if errors:
            return errors
        obj.updated_by = updated_by
        obj.save(**kwargs)
        return errors

    @classmethod
    def validation_is_necessary(cls, obj):
        from sources.models import Source
        from concepts.models import Concept

        if not isinstance(obj, Source):
            return False

        origin_source = Source.objects.get(id=obj.id)
        if origin_source.custom_validation_schema == obj.custom_validation_schema:
            return False

        return obj.custom_validation_schema is not None \
               and Concept.objects.filter(parent_id=obj.id).count() > 0

    @classmethod
    def validate_child_concepts(cls, obj):
        # If source is being configured to have a validation schema
        # we need to validate all concepts
        # according to the new schema
        from concepts.models import Concept
        from concepts.validators import ValidatorSpecifier

        concepts = Concept.objects.filter(parent_id=obj.id, is_active=True, retired=False).all()
        failed_concept_validations = []

        validator = ValidatorSpecifier()\
            .with_validation_schema(obj.custom_validation_schema)\
            .with_repo(obj)\
            .with_reference_values()\
            .get()

        for concept in concepts:
            try:
                validator.validate(concept)
                pass
            except ValidationError as validation_error:
                concept_validation_error = {'mnemonic': concept.mnemonic, 'url': concept.url, 'errors': validation_error.message_dict}
                failed_concept_validations.append(concept_validation_error)

        return failed_concept_validations


class ConceptContainerVersionModel(ResourceVersionModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    default_locale = models.TextField(default=Common.DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    version_external_id = models.TextField(null=True, blank=True)
    external_id = models.TextField(null=True, blank=True)
    _background_process_ids = SetField()

    # Used to skip saving _background_process_ids,
    # which is updated using atomic raw queries, see https://stackoverflow.com/a/33225984
    default_save_fields = None

    def __init__(self, *args, **kwargs):
        super(ConceptContainerVersionModel, self).__init__(*args, **kwargs)
        if self.default_save_fields is None:
            # This block should only get called for the first object loaded
            default_save_fields = {
                f.name for f in self._meta.fields
                if not f.auto_created
            }
            default_save_fields.difference_update({
                '_background_process_ids',
            })
            self.__class__.default_save_fields = tuple(default_save_fields)

    def save(self, **kwargs):
        if self.id is not None and 'update_fields' not in kwargs:
            # If self.id is None (meaning the object has yet to be saved)
            # then do a normal update with all fields.
            # Otherwise, make sure `update_fields` is in kwargs.
            kwargs['update_fields'] = self.default_save_fields
        super(ConceptContainerVersionModel, self).save(**kwargs)

    class Meta(ResourceVersionModel.Meta):
        abstract = True

    @property
    def owner(self):
        return self.versioned_object.owner

    @property
    def owner_name(self):
        return self.versioned_object.owner_name

    @property
    def owner_type(self):
        return self.versioned_object.owner_type

    @property
    def owner_url(self):
        return self.versioned_object.owner_url

    @property
    def parent_resource(self):
        return self.versioned_object.parent_resource

    @property
    def parent_resource_type(self):
        return self.versioned_object.parent_resource_type

    @property
    def parent_url(self):
        return self.versioned_object.parent_url

    @staticmethod
    def get_url_kwarg():
        return 'version'

    @classmethod
    def get_latest_released_version_of(cls, versioned_object):
        versions = versioned_object.get_version_model().objects.filter(versioned_object_id=versioned_object.id, is_active=True, released=True, retired=False).order_by('-created_at')
        return versions[0] if versions else None

    @classmethod
    def persist_new(cls, obj, user=None, **kwargs):
        obj.is_active = True
        if user:
            obj.created_by = user
            obj.updated_by = user
        kwargs['seed_concepts'] = True
        kwargs['seed_mappings'] = True
        return cls.persist_changes(obj, **kwargs)

    def update_version_data(self, obj=None):
        pass

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()

        # Ensure versioned object specified
        versioned_object = kwargs.pop('versioned_object', obj.versioned_object)
        if versioned_object is None:
            errors['non_field_errors'] = ['Must specify a versioned object.']
            return errors
        obj.versioned_object = versioned_object

        # Ensure mnemonic does not conflict with existing
        old_mnemonic = obj.mnemonic
        mnemonic = kwargs.pop('mnemonic', obj.mnemonic)
        if mnemonic != old_mnemonic:
            if cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj.mnemonic).exists():
                errors['mnemonic'] = ["Version with mnemonic %s already exists for %s %s." % (obj.mnemonic, cls.name, versioned_object.mnemonic)]
                return errors
        obj.mnemonic = mnemonic

        # Ensure previous version is valid
        if hasattr(obj, '_previous_version_mnemonic') and obj._previous_version_mnemonic:
            previous_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._previous_version_mnemonic)
            if not previous_version_queryset.exists():
                errors['previousVersion'] = ["Previous version %s does not exist." % obj._previous_version_mnemonic]
            elif obj.mnemonic == obj._previous_version_mnemonic:
                errors['previousVersion'] = ["Previous version cannot be the same as current version."]
            else:
                obj.previous_version = previous_version_queryset[0]
                del obj._previous_version_mnemonic

        # Ensure parent version is valid
        if hasattr(obj, '_parent_version_mnemonic') and obj._parent_version_mnemonic:
            parent_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._parent_version_mnemonic)
            if not parent_version_queryset.exists():
                errors['parentVersion'] = ["Parent version %s does not exist." % obj._parent_version_mnemonic]
            elif obj.mnemonic == obj._parent_version_mnemonic:
                errors['parentVersion'] = ["Parent version cannot be the same as current version."]
            else:
                obj.parent_version = parent_version_queryset[0]
                del obj._parent_version_mnemonic

        # If there are errors at this point, fall out before doing any more work
        if errors:
            return errors

        # Seed mappings from another version, if requested
        seed_references = kwargs.pop('seed_references', False)
        if seed_references:
            obj.seed_references()

        obj.update_version_data()

        try:
            persisted = False
            seed_concepts = kwargs.pop('seed_concepts', False)
            seed_mappings = kwargs.pop('seed_mappings', False)

            obj.save(**kwargs)

            # Seed concepts from another version, if requested
            if seed_concepts:
                obj.seed_concepts()

            # Seed mappings from another version, if requested
            if seed_mappings:
                obj.seed_mappings()

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ["Encountered an error while updating version."]
        return errors

    def add_processing(self, process_id):
        if self.id:
            # Using raw query to atomically add item to the list
            self.__class__.objects.raw_update({'_id': ObjectId(self.id)},
                                             {'$push': {'_background_process_ids': process_id}})
        # Update the current object
        self._background_process_ids.add(process_id)


    def remove_processing(self, process_id):
        if self.id:
            # Using raw query to atomically remove item from the list
            self.__class__.objects.raw_update({'_id': ObjectId(self.id)},
                                             {'$pull': {'_background_process_ids': process_id}})
        # Update the current object
        self._background_process_ids.remove(process_id)

    @property
    def is_processing(self):
        if self._background_process_ids:
            for process_id in tuple(self._background_process_ids):
                res = AsyncResult(process_id)
                if (res.successful() or res.failed()):
                    self.remove_processing(process_id)
                else:
                    return True
        if self._background_process_ids:
            return True
        else:
            return False

    def clear_processing(self):
        self._background_process_ids = set()
        self.save(update_fields=['_background_process_ids'])

    @staticmethod
    def clear_all_processing(type):
        type.objects.all().update(_background_process_ids=set())

@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if instance and created:
        Token.objects.create(user=instance)

@receiver(pre_save)
def stamp_uri(sender, instance, **kwargs):
    if issubclass(sender, BaseModel):
        if hasattr(instance, 'versioned_object'):
            instance.uri = reverse_resource_version(instance, instance.view_name)
        else:
            instance.uri = reverse_resource(instance, instance.view_name)
