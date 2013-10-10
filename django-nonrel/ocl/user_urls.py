from django.conf.urls.defaults import patterns, url
from orgs.views import OrganizationListView
from sources.views import SourceListView, SourceUpdateDetailView
from users.views import UserDetailView

__author__ = 'misternando'

extra_kwargs = {'user_is_self': True}

urlpatterns = patterns('',
    url(r'^$', UserDetailView.as_view(), extra_kwargs, name='userprofile-self-detail'),
    url(r'^orgs/$', OrganizationListView.as_view(), extra_kwargs, name='userprofile-organization-list'),
    url(r'^sources/$', SourceListView.as_view(), extra_kwargs, name='userprofile-source-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-]+)/$', SourceUpdateDetailView.as_view(), extra_kwargs, name='user-source-detail'),
)
