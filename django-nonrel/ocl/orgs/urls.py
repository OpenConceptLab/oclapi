from django.conf.urls.defaults import patterns, url, include
from orgs.models import Organization
from orgs.views import OrganizationDetailView, OrganizationListView, OrganizationMemberView
from users.views import UserListView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', OrganizationListView.as_view(), name='organization-list'),
    url(r'^(?P<org>[a-zA-Z0-9\-\.]+)/$', OrganizationDetailView.as_view(), name='organization-detail'),
    url(r'^(?P<org>[a-zA-Z0-9\-\.]+)/members/$', UserListView.as_view(), {'related_object_type': Organization, 'related_object_kwarg': 'org', 'related_object_attribute': 'members'}, name='organization-members'),
    url(r'^(?P<org>[a-zA-Z0-9\-\.]+)/members/(?P<user>[a-zA-Z0-9\-]+)/$', OrganizationMemberView.as_view(), name='organization-member-detail'),
    url(r'^(?P<org>[a-zA-Z0-9\-\.]+)/sources/', include('sources.urls')),
    url(r'^(?P<org>[a-zA-Z0-9\-\.]+)/collections/', include('conceptcollections.urls')),
)