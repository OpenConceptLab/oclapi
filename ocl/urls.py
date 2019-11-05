from django.contrib import admin
from django.conf.urls import url, patterns, include
from rest_framework import routers

from concepts.views import ConceptVersionListAllView
from mappings.views import MappingListAllView
from sources.views import SourceListView

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

    url(r'^manage/', include('manage.urls')),

    # Top-level resource endpoints
    url(r'^collections/', include('collection.urls')),
    url(r'^concepts/', ConceptVersionListAllView.as_view(), name='all-concepts'),
    url(r'^mappings/$', MappingListAllView.as_view(), name='all-mappings'),
    url(r'^orgs/', include('orgs.urls')),
    url(r'^sources/$', SourceListView.as_view(), name='source-list'),
    url(r'^users/', include('users.urls')),

    # Shortcuts to endpoints corresponding to the currently logged in user
    url(r'^user/', include('user_urls')),

    # FHIR endpoints
    url(r'^fhir/', include('fhir.urls')),

)
