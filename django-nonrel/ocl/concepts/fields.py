import urlparse
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_script_prefix, resolve
from rest_framework.fields import WritableField
from concepts.models import LocalizedText, Concept
from oclapi.fields import HyperlinkedRelatedField
from oclapi.mixins import PathWalkerMixin
from orgs.models import Organization
from sources.models import Source
from users.models import UserProfile

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
                #TODO replace this message with django translation
                if '%' in self.error_messages['invalid']:
                    msg = self.error_messages['invalid'] % value
                else:
                    msg = self.error_messages['invalid']

                raise ValidationError(msg)
            return map(lambda e: self.element_from_native(e), value)

    def element_from_native(self, element):
        return element

    def to_native(self, value):
        if value:
            return map(lambda e: self.element_to_native(e), value)

    def element_to_native(self, element):
        return element


class MappingListField(ListField):
    type_name = 'MappingListField'

    def element_to_native(self, element):
        module = __import__('mappings.serializers', fromlist=['models'])
        verbose = self.context.get('verbose', False)
        serializer_class = getattr(
            module, 'MappingDetailSerializer' if verbose else 'MappingListSerializer')
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
        external_id = element.get('external_id', None)
        if external_id:
            lt.external_id = external_id
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
        lt.locale_preferred = locale_preferred in [True, 'True', 'true', 'TRUE']
        lt.type = element.get(self.type_attr, None)
        return lt

    def element_to_native(self, element):
        module = __import__('concepts.serializers', fromlist=['models'])
        serializer_class = getattr(module, 'ConceptDescriptionSerializer' if 'description' == self.name_attr else 'ConceptNameSerializer')
        serializer = serializer_class(element)
        return serializer.data

    @property
    def name_attr(self):
        return 'name' if self.name_override is None else self.name_override

    @property
    def type_attr(self):
        return '%s_type' % self.name_attr


class SourceURLField(HyperlinkedRelatedField):
    user = None
    org = None

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
        try:
            return self.get_object_for_path(value)
        except Exception as e:
            raise ValidationError(e)

    def get_object_for_path(self, path_info):
        callback, args, kwargs = resolve(path_info)
        user_id = kwargs.get('user')
        try:
            self.user = UserProfile.objects.get(mnemonic=user_id)
        except UserProfile.DoesNotExist: pass
        org_id = kwargs.get('org')
        try:
            self.org = Organization.objects.get(mnemonic=org_id)
        except Organization.DoesNotExist: pass
        if not (self.user or self.org):
            raise ValidationError("Source owner does not exist")
        source_id = kwargs.get('source')
        if self.user:
            return Source.objects.get(
                mnemonic=source_id, parent_id=self.user.id,
                parent_type=ContentType.objects.get_for_model(UserProfile))
        else:
            return Source.objects.get(
                mnemonic=source_id, parent_id=self.org.id,
                parent_type=ContentType.objects.get_for_model(Organization))


class ConceptURLField(HyperlinkedRelatedField):
    user = None
    org = None

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
            if value == prefix:
                raise ValidationError(self.error_messages['no_match'])
            if value.startswith(prefix):
                value = '/' + value[len(prefix):]
        try:
            return self.get_object_for_path(value)
        except Exception as e:
            raise ValidationError(e)

    def get_object_for_path(self, path_info):
        callback, args, kwargs = resolve(path_info)
        user_id = kwargs.get('user')
        try:
            self.user = UserProfile.objects.get(mnemonic=user_id)
        except UserProfile.DoesNotExist: pass
        org_id = kwargs.get('org')
        try:
            self.org = Organization.objects.get(mnemonic=org_id)
        except Organization.DoesNotExist: pass
        if not (self.user or self.org):
            raise ValidationError("Concept owner does not exist")
        source_id = kwargs.get('source')
        if self.user:
            source = Source.objects.get(
                mnemonic=source_id, parent_id=self.user.id,
                parent_type=ContentType.objects.get_for_model(UserProfile))
        else:
            source = Source.objects.get(
                mnemonic=source_id, parent_id=self.org.id,
                parent_type=ContentType.objects.get_for_model(Organization))
        concept_id = kwargs.get('concept')
        return Concept.objects.get(parent_id=source.id, mnemonic=concept_id)


# class ConceptReferenceField(HyperlinkedRelatedField, PathWalkerMixin):
#
#     def from_native(self, value):
#         try:
#             http_prefix = value.startswith(('http:', 'https:'))
#         except AttributeError:
#             msg = self.error_messages['incorrect_type']
#             raise ValidationError(msg % type(value).__name__)
#
#         if http_prefix:
#             # If needed convert absolute URLs to relative path
#             value = urlparse.urlparse(value).path
#             prefix = get_script_prefix()
#             if value == prefix:
#                 raise ValidationError(self.error_messages['no_match'])
#             if value.startswith(prefix):
#                 value = '/' + value[len(prefix):]
#
#         request = self.context['request']
#         try:
#             path_obj = self.get_object_for_path(value, request)
#             if hasattr(path_obj, 'versioned_object_id'):
#                 obj = path_obj.versioned_object
#                 obj._concept_version = path_obj
#             else:
#                 obj = path_obj
#                 parent_path = self.get_parent_in_path(value, levels=2)
#                 parent = self.get_object_for_path(parent_path, request)
#                 if hasattr(parent, 'versioned_object_id'):
#                     obj._source_version = parent
#
#             return obj
#         except Exception as e:
#             raise ValidationError(e)
