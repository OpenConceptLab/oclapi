import re
from django.core.validators import RegexValidator
from django.db import models
from django_group_access import registration
from settings import NONREL_DATABASE

NAMESPACE_REGEX = re.compile(r'^[a-zA-Z0-9\-]+$')


class BaseModel(models.Model):
    mnemonic = models.CharField(max_length=255, validators=[RegexValidator(regex=NAMESPACE_REGEX)], unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RestrictedBaseModel(BaseModel):
    class Meta:
        abstract = True


registration.register(RestrictedBaseModel)


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
