from django.conf.urls.defaults import patterns, url, include
from sources.views import SourceListView, SourceRetrieveUpdateDestroyView, SourceVersionRetrieveUpdateView, SourceVersionChildListView, SourceVersionListView, SourceVersionRetrieveUpdateDestroyView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', SourceListView.as_view(), name='source-list'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/$', SourceRetrieveUpdateDestroyView.as_view(), name='source-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/versions/$', SourceVersionListView.as_view(), name='sourceversion-list'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/latest/$', SourceVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='sourceversion-latest-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/concepts/', include('concepts.urls')),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/$', SourceVersionRetrieveUpdateDestroyView.as_view(), name='sourceversion-detail'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/children/$', SourceVersionChildListView.as_view(), {'list_children': True}, name='sourceversion-child-list'),
    url(r'^(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/', include('concepts.urls'))
)
