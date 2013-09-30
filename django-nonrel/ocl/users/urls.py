from django.conf.urls.defaults import patterns, url
from orgs.views import OrganizationListView
from sources.views import SourceDetailView, SourceListView
from users.models import UserProfile
from users.views import UserListView, UserRUDView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', UserListView.as_view(), name='userprofile-list'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/$', UserRUDView.as_view(), name='userprofile-detail'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/orgs/$', OrganizationListView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'mnemonic'}, name='userprofile-orgs'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/sources/$', SourceListView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'mnemonic'}, name='userprofile-sources'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/sources/(?P<source>[a-zA-Z0-9\-]+)/$', SourceDetailView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'mnemonic'}, name='userprofile-source-detail'),
)

