import ast

from django import forms
from djangotoolbox.fields import DictField


class StringListField(forms.CharField):
    def prepare_value(self, value):
        if(value == None):
            value = ""
        return ', '.join(value)

    def to_python(self, value):
        if not value:
            return []
        return [item.strip() for item in value.split(',')]


class DictionaryField(forms.CharField):
    def generate_dictfield(self, field_name, field, **kwargs):
        defaults = {
            'required': field.required,
            'initial': field.default,
            'label': self.get_field_label(field_name, field),
            'help_text': self.get_field_help_text(field),
        }
        defaults.update(kwargs)
        return DictField(**defaults)

    def to_python(self, value):
        if isinstance(value, basestring):
            value = ast.literal_eval(value)
            return value
        if isinstance(value, dict):
            return value
        raise ValueError('"%s" could not be converted to a dict.' % value)

