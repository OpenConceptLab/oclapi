from django.conf.urls.defaults import patterns, url
from sources.views import SourceListView, SourceUpdateDetailView, SourceVersionUpdateDetailView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', SourceListView.as_view(), name='source-list'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/$', SourceUpdateDetailView.as_view(), name='source-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/$', SourceVersionUpdateDetailView.as_view(), name='sourceversion-detail'),
)
