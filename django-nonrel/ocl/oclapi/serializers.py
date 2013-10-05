from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializerOptions, ModelSerializer

from oclapi.fields import HyperlinkedIdentityField


__author__ = 'misternando'


class HyperlinkedModelSerializerOptions(ModelSerializerOptions):
    """
    Options for HyperlinkedModelSerializer
    """
    def __init__(self, meta):
        super(HyperlinkedModelSerializerOptions, self).__init__(meta)
        self.view_name = getattr(meta, 'view_name', None)
        self.lookup_field = getattr(meta, 'lookup_field', None)


class HyperlinkedModelSerializer(ModelSerializer):
    """
    A subclass of ModelSerializer that uses hyperlinked relationships,
    instead of primary key relationships.
    """
    _options_class = HyperlinkedModelSerializerOptions
    _default_view_name = '%(model_name)s-detail'
    _hyperlink_field_class = HyperlinkedRelatedField

    def get_default_fields(self):
        fields = super(HyperlinkedModelSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)

        if 'url' not in fields:
            url_field = HyperlinkedIdentityField(
                view_name=self.opts.view_name,
                lookup_field=self.opts.lookup_field
            )
            ret = self._dict_class()
            ret['url'] = url_field
            ret.update(fields)
            fields = ret

        return fields

    def get_pk_field(self, model_field):
        if self.opts.fields and model_field.name in self.opts.fields:
            return self.get_field(model_field)

    def get_related_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a flat relational field.
        """
        # TODO: filter queryset using:
        # .using(db).complex_filter(self.rel.limit_choices_to)
        kwargs = {
            'queryset': related_model._default_manager,
            'view_name': self._get_default_view_name(related_model),
            'many': to_many
        }

        if model_field:
            kwargs['required'] = not(model_field.null or model_field.blank)

        if self.opts.lookup_field:
            kwargs['lookup_field'] = self.opts.lookup_field

        return self._hyperlink_field_class(**kwargs)

    def get_identity(self, data):
        """
        This hook is required for bulk update.
        We need to override the default, to use the url as the identity.
        """
        try:
            return data.get('url', None)
        except AttributeError:
            return None

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

