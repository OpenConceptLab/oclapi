from django.conf.urls.defaults import patterns, url
from orgs.models import Organization
from orgs.views import OrganizationDetailView, OrganizationListView, OrganizationMemberView
from sources.views import SourceDetailView, SourceListView
from users.views import UserListView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', OrganizationListView.as_view(), name='organization-list'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/$', OrganizationDetailView.as_view(), name='organization-detail'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/members/$', UserListView.as_view(), {'related_object_type': Organization, 'related_object_kwarg': 'mnemonic'}, name='organization-members'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/members/(?P<uid>[a-zA-Z0-9\-]+)/$', OrganizationMemberView.as_view(), name='organization-member-detail'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/sources/$', SourceListView.as_view(), {'related_object_type': Organization, 'related_object_kwarg': 'mnemonic'}, name='organization-source-list'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/sources/(?P<source>[a-zA-Z0-9\-]+)/$', SourceDetailView.as_view(), {'related_object_type': Organization, 'related_object_kwarg': 'mnemonic'}, name='organization-source-detail'),
)