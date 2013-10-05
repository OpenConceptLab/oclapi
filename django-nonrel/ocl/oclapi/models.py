import re
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django_group_access import registration
from settings import NONREL_DATABASE

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

registration.register(SubResourceBaseModel)


class NonrelMixin(object):

    @classmethod
    def db_for_read(cls):
        return NONREL_DATABASE

    @classmethod
    def db_for_write(cls):
        return NONREL_DATABASE

    @classmethod
    def allow_relation(cls, cls2, **hints):
        return cls2 == cls

    @classmethod
    def allow_syncdb(cls, db):
        return db == NONREL_DATABASE
