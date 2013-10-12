from django.contrib import admin
from django.conf.urls.defaults import url, patterns, include
from django.core.urlresolvers import NoReverseMatch
from rest_framework import routers
from rest_framework.reverse import reverse

admin.autodiscover()


# Routers provide an easy way of automatically determining the URL conf
router = routers.DefaultRouter()
urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'ocl.views.home', name='home'),
    # url(r'^ocl/', include('ocl.foo.urls')),
    url(r'^', include(router.urls)),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/$', 'rest_framework.authtoken.views.obtain_auth_token'),
    url(r'^orgs/', include('orgs.urls')),
    url(r'^sources/', include('sources.urls')),
    url(r'^users/', include('users.urls')),
    url(r'^user/', include('user_urls')),
)


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
    versioned_object = resource.versioned_object
    kwargs = kwargs or {}
    kwargs.update({
        resource.get_url_kwarg(): resource.mnemonic
    })
    return reverse_resource(versioned_object, viewname, args, kwargs, request, format, **extra)