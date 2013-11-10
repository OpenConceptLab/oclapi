from django.conf.urls.defaults import patterns, url
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', ConceptCreateView.as_view(), name='concept-list'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
#    url(r'^(?P<source>[a-zA-Z0-9\-]+)/versions/$', SourceVersionListView.as_view(), name='sourceversion-list'),
#    url(r'^(?P<source>[a-zA-Z0-9\-]+)/latest/$', SourceVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='sourceversion-latest-detail'),
#    url(r'^(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/$', SourceVersionRetrieveUpdateDestroyView.as_view(), name='sourceversion-detail'),
#    url(r'^(?P<source>[a-zA-Z0-9\-]+)/(?P<version>[a-zA-Z0-9\-]+)/children/$', SourceVersionChildListView.as_view(), {'list_children': True}, name='sourceversion-child-list'),
)

