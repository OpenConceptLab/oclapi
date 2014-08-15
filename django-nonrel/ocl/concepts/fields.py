from django.core.exceptions import ValidationError
from rest_framework.fields import WritableField
from concepts.models import LocalizedText

__author__ = 'misternando'


class ListField(WritableField):
    type_name = 'ListField'
    type_label = 'list'

    def from_native(self, value):
        super(ListField, self).validate(value)
        if not value:
            return value
        else:
            if not isinstance(value, list):
                msg = self.error_messages['invalid'] % value
                raise ValidationError(msg)
            return map(lambda e: self.element_from_native(e), value)

    def element_from_native(self, element):
        return element

    def to_native(self, value):
        return map(lambda e: self.element_to_native(e), value)

    def element_to_native(self, element):
        return element


class LocalizedTextListField(ListField):
    type_name = 'LocalizedTextListField'

    def __init__(self, **kwargs):
        self.name_override = kwargs.pop('name_override', None)
        super(LocalizedTextListField, self).__init__(**kwargs)

    def element_from_native(self, element):
        if not element or not isinstance(element, dict):
            msg = self.error_messages['invalid'] % element
            raise ValidationError(msg)
        lt = LocalizedText()
        name = element.get(self.name_attr, None)
        if name is None or not isinstance(name, unicode):
            msg = self.error_messages['invalid'] % element
            raise ValidationError(msg)
        lt.name = name
        locale = element.get('locale', None)
        if locale is None or not isinstance(locale, unicode):
            msg = self.error_messages['invalid'] % element
            raise ValidationError(msg)
        lt.locale = locale
        lt.locale_preferred = element.get('localePreferred', False)
        lt.type = element.get('type', None)
        return lt

    def element_to_native(self, element):
        return {
            self.name_attr: element.name,
            'locale': element.locale,
            'localePreferred': element.locale_preferred,
            'type': element.type
        }

    @property
    def name_attr(self):
        return 'name' if self.name_override is None else self.name_override
