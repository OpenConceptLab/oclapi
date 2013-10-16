from rest_framework.relations import HyperlinkedIdentityField
from urls import reverse_resource, reverse_resource_version


class HyperlinkedResourceIdentityField(HyperlinkedIdentityField):

    def get_url(self, obj, view_name, request, format):
        return reverse_resource(obj, view_name, request=request, format=format)


class HyperlinkedResourceOwnerField(HyperlinkedResourceIdentityField):

    def get_url(self, obj, view_name, request, format):
        if not hasattr(obj, 'parent'):
            raise Exception('Cannot get parent URL for %s.  %s has no parent.' % obj)
        return reverse_resource(obj.parent, view_name, request=request, format=format)


class HyperlinkedVersionedResourceIdentityField(HyperlinkedIdentityField):

    def get_url(self, obj, view_name, request, format):
        return reverse_resource(obj.versioned_object, view_name, request=request, format=format)


class HyperlinkedResourceVersionIdentifyField(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        return reverse_resource_version(obj, view_name, request=request, format=format)




