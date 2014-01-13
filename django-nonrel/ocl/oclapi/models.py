import re
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models

NAMESPACE_REGEX = re.compile(r'^[a-zA-Z0-9\-\.]+$')


class BaseModel(models.Model):
    """
    Base model from which all resources inherit.  Contains timestamps and is_active field for logical deletion.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


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
    (A Source is a base resource, but an Organization is not.)
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    owner = models.ForeignKey(User, db_index=False)
    parent_type = models.ForeignKey(ContentType, db_index=False)
    parent_id = models.TextField()
    parent = generic.GenericForeignKey('parent_type', 'parent_id')

    class Meta:
        abstract = True
        unique_together = ('mnemonic', 'parent_id')

    def __unicode__(self):
        return self.mnemonic

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
    next_version = models.ForeignKey('self', related_name='previous', null=True, blank=True, db_index=False)
    previous_version = models.ForeignKey('self', related_name='next', null=True, blank=True, db_index=False)
    parent_version = models.ForeignKey('self', related_name='child', null=True, blank=True, db_index=False)

    class Meta:
        abstract = True
        unique_together = ('mnemonic', 'versioned_object_id')

    def __unicode__(self):
        return self.mnemonic

    @property
    def previous_version_mnemonic(self):
        return self.previous_version.mnemonic if self.previous_version else None

    @property
    def parent_version_mnemonic(self):
        return self.parent_version.mnemonic if self.parent_version else None

    @property
    def parent_resource(self):
        return self.versioned_object.parent_resource

    @property
    def parent_resource_type(self):
        return self.versioned_object.parent_resource_type

    @classmethod
    def get_latest_version_of(cls, versioned_object):
        versions = versioned_object.get_version_model().objects.filter(versioned_object_id=versioned_object.id, is_active=True).order_by('-created_at')
        return versions[0] if versions else None
