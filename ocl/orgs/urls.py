from django.conf.urls import patterns, url, include
from orgs.models import Organization
from orgs.views import OrganizationDetailView, OrganizationListView, OrganizationMemberView
from users.views import UserListView
from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', OrganizationListView.as_view(), name='organization-list'),
    url(r'^(?P<org>' + NAMESPACE_PATTERN + ')/$', OrganizationDetailView.as_view(), name='organization-detail'),
    url(r'^(?P<org>' + NAMESPACE_PATTERN + ')/members/$', UserListView.as_view(), {'related_object_type': Organization, 'related_object_kwarg': 'org', 'related_object_attribute': 'members'}, name='organization-members'),
    url(r'^(?P<org>' + NAMESPACE_PATTERN + ')/members/(?P<user>' + NAMESPACE_PATTERN + ')/$', OrganizationMemberView.as_view(), name='organization-member-detail'),
    url(r'^(?P<org>' + NAMESPACE_PATTERN + ')/sources/', include('sources.urls')),
    url(r'^(?P<org>' + NAMESPACE_PATTERN + ')/collections/', include('collection.urls')),
)