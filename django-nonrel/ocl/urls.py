from django.contrib import admin
from django.conf.urls.defaults import url, patterns, include
from rest_framework import routers
from sources.views import SourceListView
from users.views import UserDetailView
from orgs.views import OrganizationListView

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
    url(r'^users/', include('users.urls')),
    # These views pertain to the logged-in user
    url(r'^user/$', UserDetailView.as_view(), {'user_is_self': True}, name='userprofile-self-detail'),
    url(r'^user/orgs/$', OrganizationListView.as_view(), {'user_is_self': True}, name='userprofile-organization-list'),
    url(r'^user/sources/$', SourceListView.as_view(), name='userprofile-source-list'),
)
