import re
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django_group_access import registration

NAMESPACE_REGEX = re.compile(r'^[a-zA-Z0-9\-]+$')


class BaseModel(models.Model):
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)], unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.mnemonic


class SubResourceBaseModel(BaseModel):
    parent_type = models.ForeignKey(ContentType)
    parent_id = models.TextField()
    parent = generic.GenericForeignKey('parent_type', 'parent_id')

    class Meta:
        abstract = True

    @property
    def parent_resource(self):
        return self.parent.mnemonic

    @property
    def parent_resource_type(self):
        return self.parent.resource_type

registration.register(SubResourceBaseModel)


class ResourceVersionModel(BaseModel):
    versioned_object_id = models.TextField()
    versioned_object_type = models.ForeignKey(ContentType)
    versioned_object = generic.GenericForeignKey('versioned_object_type', 'versioned_object_id')
    released = models.BooleanField(default=False, blank=True)
    previous_version = models.OneToOneField('self', related_name='next_version', null=True, blank=True)
    parent_version = models.OneToOneField('self', related_name='child_version', null=True, blank=True)

    class Meta:
        abstract = True