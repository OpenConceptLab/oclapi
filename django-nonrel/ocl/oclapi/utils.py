from django.core.urlresolvers import NoReverseMatch
from rest_framework.reverse import reverse

__author__ = 'misternando'


def reverse_resource(resource, viewname, args=None, kwargs=None, request=None, format=None, **extra):
    kwargs = kwargs or {}
    parent = resource
    while parent is not None:
        if not hasattr(parent, 'get_url_kwarg'):
            return NoReverseMatch('Cannot get URL kwarg for %s' % resource)
        kwargs.update({parent.get_url_kwarg(): parent.mnemonic})
        parent = parent.parent if hasattr(parent, 'parent') else None
    return reverse(viewname, args, kwargs, request, format, **extra)


def reverse_resource_version(resource, viewname, args=None, kwargs=None, request=None, format=None, **extra):
    kwargs = kwargs or {}
    kwargs.update({
        resource.get_url_kwarg(): resource.mnemonic
    })
    return reverse_resource(resource.versioned_object, viewname, args, kwargs, request, format, **extra)