import re
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from djangotoolbox.fields import DictField, ListField
from rest_framework.authtoken.models import Token
from oclapi.utils import reverse_resource, reverse_resource_version
from settings import DEFAULT_LOCALE

NAMESPACE_REGEX = re.compile(r'^[a-zA-Z0-9\-\.]+$')

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
    extras = DictField(null=True, blank=True)
    uri = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True

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

    def clean(self):
        if self == self.parent_version:
            raise ValidationError('version cannot be its own parent')

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

    @classmethod
    def get_latest_version_of(cls, versioned_object):
        versions = versioned_object.get_version_model().objects.filter(versioned_object_id=versioned_object.id, is_active=True).order_by('-created_at')
        return versions[0] if versions else None


class ConceptContainerModel(SubResourceBaseModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    external_id = models.TextField(null=True, blank=True)

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
            version = version_model.for_base_object(obj, 'INITIAL')
            version.released = True
            version.save()
            version.mnemonic = version.id
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
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
        if errors:
            return errors
        obj.updated_by = updated_by
        obj.save(**kwargs)
        return errors


class ConceptContainerVersionModel(ResourceVersionModel):
    name = models.TextField()
    full_name = models.TextField(null=True, blank=True)
    default_locale = models.TextField(default=DEFAULT_LOCALE, blank=True)
    supported_locales = ListField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    external_id = models.TextField(null=True, blank=True)

    class Meta(ResourceVersionModel.Meta):
        abstract = True

    @property
    def owner(self):
        return self.versioned_object.owner

    @property
    def owner_name(self):
        return self.versioned_object.ower_name

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
        versions = versioned_object.get_version_model().objects.filter(versioned_object_id=versioned_object.id, is_active=True, released=True).order_by('-created_at')
        return versions[0] if versions else None

    @classmethod
    def persist_new(cls, obj, **kwargs):
        obj.is_active = True
        kwargs['seed_concepts'] = True
        kwargs['seed_mappings'] = True
        return cls.persist_changes(obj, **kwargs)

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

        # Seed concepts from another version, if requested
        seed_concepts = kwargs.pop('seed_concepts', False)
        if seed_concepts:
            obj.seed_concepts()

        # Seed mappings from another version, if requested
        seed_mappings = kwargs.pop('seed_mappings', False)
        if seed_mappings:
            obj.seed_mappings()

        # See if we need to toggle the released flag
        previous_release = None
        if hasattr(obj, '_was_released'):
            if obj.released and not obj._was_released:
                previous_release = cls.objects.get(versioned_object_id=obj.versioned_object.id, released=True)
            del obj._was_released

        persisted = False
        try:
            if previous_release:
                previous_release.released = False
                previous_release.save()
            obj.save(**kwargs)
            persisted = True
        finally:
            if not persisted:
                if previous_release:
                    previous_release.released = True
                    previous_release.save()
                errors['non_field_errors'] = ["Encountered an error while updating version."]
        return errors


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