import urlparse
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_script_prefix
from oclapi.fields import HyperlinkedRelatedField
from oclapi.views import PathWalkerMixin

__author__ = 'misternando'


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

