from django.contrib import admin
from django.conf.urls.defaults import url, patterns, include
from rest_framework import routers
from concepts.views import ConceptListView

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
    url(r'^collections/', include('conceptcollections.urls')),
    url(r'^concepts/', ConceptListView.as_view(), name='full-concept'),
    url(r'^orgs/', include('orgs.urls')),
    url(r'^sources/', include('sources.urls')),
    url(r'^users/', include('users.urls')),
    url(r'^user/', include('user_urls')),
)





