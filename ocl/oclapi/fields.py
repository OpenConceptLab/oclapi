"""
Serializer fields that deal with relationships among entities
(e.g. resources, sub-resources, resource versions) in the OCL Object Model.
"""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.relations import HyperlinkedIdentityField, HyperlinkedRelatedField


class HyperlinkedRelatedField(HyperlinkedRelatedField):
    pk_field = 'mnemonic'

    def __init__(self, *args, **kwargs):
        self.lookup_kwarg = kwargs.pop('lookup_kwarg', None)
        super(HyperlinkedRelatedField, self).__init__(*args, **kwargs)

    def get_object(self, queryset, view_name, view_args, view_kwargs):
        lookup = view_kwargs.get(self.lookup_kwarg, None)
        if lookup is not None:
            filter_kwargs = {self.pk_field: lookup}
        else:
            raise ObjectDoesNotExist()

        return queryset.get(**filter_kwargs)

    def get_url(self, obj, view_name, request, format):
        return obj.url


class HyperlinkedResourceIdentityField(HyperlinkedIdentityField):
    """
    This is a field that generates a URL for any resource or sub-resource.
    e.g. GET /orgs
    returns a list of items, each containing a "url" field that specifies a distinct Organization resource:
    "url": "https://api.openconceptlab.org/v1/orgs/My-Organization"
    """
    def get_url(self, obj, view_name, request, format):
        return obj.url


class HyperlinkedVersionedResourceIdentityField(HyperlinkedIdentityField):
    """
    This is a field that generates a URL for a versioned resource from one of its versions.
    e.g. GET /orgs/:org/sources/:source/:version
    returns a SourceVersion resource that has a "sourceUrl" field denoting the Source that it versions:
    "sourceUrl": "https://api.openconceptlab.org/v1/orgs/Regenstrief/sources/loinc2"
    """
    def get_url(self, obj, view_name, request, format):
        return obj.versioned_object.url


class HyperlinkedResourceVersionIdentityField(HyperlinkedIdentityField):
    """
    This is a field that generates a URL for a resource version, or one of its attributes
    e.g. GET /orgs/:org/sources/:source/:version
    returns a SourceVersion resource with a previousVersionUrl denoting the previous version of this version's source:
    "previousVersionUrl": "https://api.openconceptlab.org/v1/orgs/Regenstrief/sources/loinc2/2.1",
    """
    def __init__(self, *args, **kwargs):
        self.related_attr = kwargs.pop('related_attr', None)
        super(HyperlinkedResourceVersionIdentityField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        o = obj
        if self.related_attr and hasattr(obj, self.related_attr):
            o = getattr(obj, self.related_attr)
        return super(HyperlinkedResourceVersionIdentityField, self).field_to_native(o, field_name) if o else None

    def get_url(self, obj, view_name, request, format):
        return obj.url
