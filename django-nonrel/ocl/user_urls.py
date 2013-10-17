from django.conf.urls.defaults import patterns, url
from orgs.views import OrganizationListView
from sources.views import SourceListView, SourceUpdateDetailView, SourceVersionUpdateDetailView, SourceVersionListView
from users.views import UserDetailView

__author__ = 'misternando'

extra_kwargs = {'user_is_self': True}

urlpatterns = patterns('',
    url(r'^$', UserDetailView.as_view(), extra_kwargs, name='userprofile-self-detail'),
    url(r'^orgs/$', OrganizationListView.as_view(), extra_kwargs, name='userprofile-organization-list'),
    url(r'^sources/$', SourceListView.as_view(), extra_kwargs, name='userprofile-source-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-]+)/$', SourceUpdateDetailView.as_view(), extra_kwargs, name='user-source-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-]+)/latest/$', SourceVersionUpdateDetailView.as_view(), {'user_is_self': True, 'is_latest': True}, name='sourceversion-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/$', SourceVersionUpdateDetailView.as_view(), extra_kwargs, name='sourceversion-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/children/$', SourceVersionListView.as_view(), extra_kwargs, name='sourceversion-child-list'),
)
