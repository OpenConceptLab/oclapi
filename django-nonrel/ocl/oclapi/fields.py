from rest_framework.relations import HyperlinkedIdentityField
from rest_framework.reverse import reverse


class DynamicHyperlinkedIdentifyField(HyperlinkedIdentityField):

    def __init__(self, *args, **kwargs):
        self.detail_url_kwarg = kwargs.pop('detail_url_kwarg')
        self.related_lookup_field = kwargs.pop('related_lookup_field')
        self.related_lookup_value = kwargs.pop('related_lookup_value')
        super(DynamicHyperlinkedIdentifyField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, fmt):
        lookup_field = getattr(obj, self.lookup_field)
        if self.related_lookup_field and self.related_lookup_value:
            kwargs = {self.related_lookup_field: self.related_lookup_value, self.detail_url_kwarg: lookup_field}
        else:
            kwargs = {self.lookup_field: lookup_field}
        return reverse(view_name, kwargs=kwargs, request=request, format=fmt)

