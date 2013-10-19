import re
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django_group_access import registration

NAMESPACE_REGEX = re.compile(r'^[a-zA-Z0-9\-]+$')


class BaseModel(models.Model):
    """
    Base model for all objects in the system.  Contains timestamps and is_active field for logical deletion
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BaseResourceModel(BaseModel):
    """
    A base resource has a mnemonic that is unique across all objects of its type.
    A base resource may contain sub-resources
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)], unique=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.mnemonic


class SubResourceBaseModel(BaseModel):
    """
    A sub-resource is an object that exists within the scope of a parent resource.
    Its mnemonic is unique within the scope of its parent resource.
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
    def parent_resource(self):
        return self.parent.mnemonic

    @property
    def parent_resource_type(self):
        return self.parent.resource_type

registration.register(SubResourceBaseModel)


class ResourceVersionModel(BaseModel):
    """
    This model represents a version of a resource.  It has links to its base resource,
    as well as its parent and previous versions (if any)
    """
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    versioned_object_id = models.TextField()
    versioned_object_type = models.ForeignKey(ContentType, db_index=False)
    versioned_object = generic.GenericForeignKey('versioned_object_type', 'versioned_object_id')
    released = models.BooleanField(default=False, blank=True)
    previous_version = models.ForeignKey('self', related_name='next_version', null=True, blank=True, db_index=False)
    parent_version = models.ForeignKey('self', related_name='child_version', null=True, blank=True, db_index=False)

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
