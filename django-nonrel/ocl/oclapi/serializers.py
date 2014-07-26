from rest_framework import serializers
from rest_framework.pagination import PaginationSerializer
from rest_framework.serializers import HyperlinkedModelSerializerOptions
from oclapi.fields import HyperlinkedVersionedResourceIdentityField, HyperlinkedResourceVersionIdentityField


class HeaderPaginationSerializer(PaginationSerializer):

    def __init__(self, *args, **kwargs):
        self._headers_and_data = None
        super(HeaderPaginationSerializer, self).__init__(*args, **kwargs)

    @property
    def data(self):
        if self._headers_and_data is None:
            self._populate_headers_and_data()
        return self._headers_and_data['data']

    @property
    def headers(self):
        if self._headers_and_data is None:
            self._populate_headers_and_data()
        return self._headers_and_data['headers']

    def _populate_headers_and_data(self):
        self._headers_and_data = {}
        obj = self.object
        page_fields = self.to_native(obj)
        self._headers_and_data['headers'] = {}
        self._headers_and_data['headers']['count'] = page_fields['count']
        self._headers_and_data['headers']['next'] = page_fields['next']
        self._headers_and_data['headers']['previous'] = page_fields['previous']
        self._headers_and_data['data'] = page_fields['results']


class ResourceVersionSerializerOptions(HyperlinkedModelSerializerOptions):

    def __init__(self, meta):
        super(ResourceVersionSerializerOptions, self).__init__(meta)
        self.versioned_object_view_name = getattr(meta, 'versioned_object_view_name', None)
        self.versioned_object_field_name = getattr(meta, 'versioned_object_field_name', None)


class ResourceVersionSerializer(serializers.Serializer):
    """
    A ResourceVersionSerializer generates a URL for a particular version of a resource,
    and another URL for the resource that is versioned.
    It does not extend HyperlinkedResourceSerializer, because its URL-generation strategy is different.
    """
    _options_class = ResourceVersionSerializerOptions
    _default_view_name = '%(model_name)s-detail'

    def get_default_fields(self):
        fields = super(ResourceVersionSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)

        if self.opts.versioned_object_view_name is None:
            object = self.object[0] if self.many and len(self.object) > 0 else self.object
            if object:
                versioned_object_model = object.versioned_object_type.model_class()
                self.opts.versioned_object_view_name = self._get_default_view_name(versioned_object_model)

        ret = self._dict_class()

        if 'versionUrl' not in fields:
            url_field = HyperlinkedResourceVersionIdentityField(
                view_name=self.opts.view_name,
            )
            ret['versionUrl'] = url_field

        versioned_object_field_name = self.opts.versioned_object_field_name or 'versionedObjectUrl'
        if versioned_object_field_name not in fields:
            url_field = HyperlinkedVersionedResourceIdentityField(
                view_name=self.opts.versioned_object_view_name,
            )
            ret[versioned_object_field_name] = url_field

        ret.update(fields)
        fields = ret

        return fields

    def _get_default_view_name(self, model):
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs
