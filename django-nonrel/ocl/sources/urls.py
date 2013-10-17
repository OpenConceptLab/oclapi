from django.conf.urls.defaults import patterns, url
from sources.views import SourceListView, SourceUpdateDetailView, SourceVersionUpdateDetailView, SourceVersionListView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', SourceListView.as_view(), name='source-list'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/$', SourceUpdateDetailView.as_view(), name='source-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/latest/$', SourceVersionUpdateDetailView.as_view(), {'is_latest': True}, name='sourceversion-latest-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/$', SourceVersionUpdateDetailView.as_view(), name='sourceversion-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/children/$', SourceVersionListView.as_view(), {'list_children': True}, name='sourceversion-child-list'),
)
