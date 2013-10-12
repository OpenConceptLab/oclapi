from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializerOptions
from oclapi.fields import HyperlinkedResourceIdentityField, HyperlinkedResourceOwnerField, HyperlinkedResourceVersionIdentityField


class LinkedResourceSerializer(serializers.Serializer):
    _options_class = HyperlinkedModelSerializerOptions
    _default_view_name = '%(model_name)s-detail'

    def get_default_fields(self):
        fields = super(LinkedResourceSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)

        if 'url' not in fields:
            url_field = HyperlinkedResourceIdentityField(
                view_name=self.opts.view_name,
            )
            ret = self._dict_class()
            ret['url'] = url_field
            ret.update(fields)
            fields = ret

        return fields

    def _get_default_view_name(self, model):
        """
        Return the view name to use if 'view_name' is not specified in 'Meta'
        """
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs


class LinkedSubResourceSerializer(LinkedResourceSerializer):

    def get_default_fields(self):
        default_fields = super(LinkedSubResourceSerializer, self).get_default_fields()
        default_fields.update({
            'ownerUrl': HyperlinkedResourceOwnerField(view_name=self._get_default_view_name(self.object.parent))
        })
        return default_fields


class ResourceVersionSerializer(serializers.Serializer):
    _options_class = HyperlinkedModelSerializerOptions
    _default_view_name = '%(model_name)s-detail'

    def get_default_fields(self):
        fields = super(ResourceVersionSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            versioned_object_model = self.object.versioned_object_type.model_class()
            self.opts.view_name = self._get_default_view_name(versioned_object_model)

        if 'versioned_object_url' not in fields:
            url_field = HyperlinkedResourceVersionIdentityField(
                view_name=self.opts.view_name,
            )
            ret = self._dict_class()
            ret['versioned_object_url'] = url_field
            ret.update(fields)
            fields = ret

        return fields

    def _get_default_view_name(self, model):
        """
        Return the view name to use if 'view_name' is not specified in 'Meta'
        """
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs
