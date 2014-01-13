"""
Serializer fields that deal with relationships among entities
(e.g. resources, sub-resources, resource versions) in the OCL Object Model.
"""
from rest_framework.relations import HyperlinkedIdentityField
from oclapi.utils import reverse_resource, reverse_resource_version


class HyperlinkedResourceIdentityField(HyperlinkedIdentityField):
    """
    This is a field that generates a URL for any resource or sub-resource.
    e.g. GET /orgs
    returns a list of items, each containing a "url" field that specifies a distinct Organization resource:
    "url": "https://api.openconceptlab.org/v1/orgs/My-Organization"
    """
    def get_url(self, obj, view_name, request, format):
        return reverse_resource(obj, view_name, request=request, format=format)


class HyperlinkedResourceOwnerField(HyperlinkedResourceIdentityField):
    """
    This is a field that generates a URL for the parent of a sub-resource.
    e.g. GET /orgs/:org/sources/:source
    returns a Source resource that has a "ownerUrl" field denoting its owner Organization:
    "ownerUrl": "https://api.openconceptlab.org/v1/orgs/WHO"
    """
    def get_url(self, obj, view_name, request, format):
        if not hasattr(obj, 'parent'):
            raise Exception('Cannot get parent URL for %s.  %s has no parent.' % obj)
        return reverse_resource(obj.parent, view_name, request=request, format=format)


class HyperlinkedVersionedResourceIdentityField(HyperlinkedIdentityField):
    """
    This is a field that generates a URL for a versioned resource from one of its versions.
    e.g. GET /orgs/:org/sources/:source/:version
    returns a SourceVersion resource that has a "sourceUrl" field denoting the Source that it versions:
    "sourceUrl": "https://api.openconceptlab.org/v1/orgs/Regenstrief/sources/loinc2"
    """
    def get_url(self, obj, view_name, request, format):
        return reverse_resource(obj.versioned_object, view_name, request=request, format=format)


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
        return reverse_resource_version(obj, view_name, request=request, format=format)




