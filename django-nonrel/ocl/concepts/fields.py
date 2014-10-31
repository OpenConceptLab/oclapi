import urlparse
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_script_prefix
from rest_framework.fields import WritableField
from concepts.models import LocalizedText
from oclapi.fields import HyperlinkedRelatedField
from oclapi.mixins import PathWalkerMixin

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


class MappingListField(ListField):
    type_name = 'MappingListField'

    def element_to_native(self, element):
        module = __import__('mappings.serializers', fromlist=['models'])
        serializer_class = getattr(module, 'MappingRetrieveDestroySerializer')
        serializer = serializer_class(element)
        return serializer.data


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
        locale_preferred = element.get('locale_preferred', False)
        lt.locale_preferred = locale_preferred in ['True', 'true', 'TRUE']
        lt.type = element.get(self.type_attr, None)
        return lt

    def element_to_native(self, element):
        return {
            self.name_attr: element.name,
            'locale': element.locale,
            'locale_preferred': element.locale_preferred,
            self.type_attr: element.type
        }

    @property
    def name_attr(self):
        return 'name' if self.name_override is None else self.name_override

    @property
    def type_attr(self):
        return '%s_type' % self.name_attr


class ConceptReferenceField(HyperlinkedRelatedField, PathWalkerMixin):

    def from_native(self, value):
        try:
            http_prefix = value.startswith(('http:', 'https:'))
        except AttributeError:
            msg = self.error_messages['incorrect_type']
            raise ValidationError(msg % type(value).__name__)

        if http_prefix:
            # If needed convert absolute URLs to relative path
            value = urlparse.urlparse(value).path
            prefix = get_script_prefix()
            if value.startswith(prefix):
                value = '/' + value[len(prefix):]

        request = self.context['request']
        path_obj = self.get_object_for_path(value, request)
        if hasattr(path_obj, 'versioned_object_id'):
            obj = path_obj.versioned_object
            obj._concept_version = path_obj
        else:
            obj = path_obj
            parent_path = self.get_parent_in_path(value, levels=2)
            parent = self.get_object_for_path(parent_path, request)
            if hasattr(parent, 'versioned_object_id'):
                obj._source_version = parent

        return obj