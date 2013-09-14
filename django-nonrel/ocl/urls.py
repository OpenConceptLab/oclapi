from django.contrib import admin
from django.conf.urls.defaults import url, patterns, include
from rest_framework import routers
from accounts.models import Organization
from accounts.views import UserListView, UserDetailView, OrganizationListView, OrganizationDetailView, OrganizationMemberView, UserRUDView

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
    url(r'^orgs/$', OrganizationListView.as_view(), name='organization-list'),
    url(r'^orgs/(?P<pk>[0-9]+)/$', OrganizationDetailView.as_view(), name='organization-detail'),
    url(r'^orgs/(?P<pk>[0-9]+)/members/$', UserListView.as_view(), {'related_object_type': Organization}, name='organization-members'),
    url(r'^orgs/(?P<pk>[0-9]+)/members/(?P<uid>[0-9]+)/$', OrganizationMemberView.as_view(), name='organization-member-detail'),
    url(r'^users/$', UserListView.as_view(), name='userprofile-list'),
    url(r'^users/(?P<pk>[0-9]+)/$', UserRUDView.as_view(), name='userprofile-detail'),
    # These views pertain to the logged-in user
    url(r'^user/$', UserDetailView.as_view(), {'user_is_self': True}, name='userprofile-self-detail'),
    url(r'^user/orgs/$', OrganizationListView.as_view(), {'user_is_self': True}, name='userprofile-organization-list'),
)
