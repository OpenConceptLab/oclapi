from django.conf.urls.defaults import patterns, url
from orgs.views import OrganizationListView
from users.models import UserProfile
from users.views import UserListView, UserRUDView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', UserListView.as_view(), name='userprofile-list'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/$', UserRUDView.as_view(), name='userprofile-detail'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/orgs/$', OrganizationListView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'mnemonic'}, name='userprofile-orgs'),
)

