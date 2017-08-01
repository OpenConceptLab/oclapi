from djangotoolbox.fields import ListField, DictField
from django.db import models
from .customform import StringListField, DictionaryField


class ListOverrideField(ListField):
    def formfield(self, **kwargs):
        return models.Field.formfield(self, StringListField, **kwargs)


class DictOverrideField(DictField):
    def formfield(self, **kwargs):
        return models.Field.formfield(self, DictionaryField, **kwargs)
