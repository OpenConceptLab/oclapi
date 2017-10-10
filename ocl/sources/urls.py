from django.conf.urls import patterns, url, include
from sources.feeds import SourceFeed
from sources.views import SourceListView, SourceRetrieveUpdateDestroyView, SourceVersionRetrieveUpdateView, \
    SourceVersionChildListView, SourceVersionListView, SourceVersionRetrieveUpdateDestroyView, SourceExtrasView, \
    SourceExtraRetrieveUpdateDestroyView, SourceVersionExportView, SourceVersionProcessingView
from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', SourceListView.as_view(), name='source-list'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/$', SourceRetrieveUpdateDestroyView.as_view(), name='source-detail'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/atom/$', SourceFeed()),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/versions/$', SourceVersionListView.as_view(), name='sourceversion-list'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/latest/$', SourceVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='sourceversion-latest-detail'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/concepts/', include('concepts.urls')),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/mappings/', include('mappings.urls')),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/extras/$', SourceExtrasView.as_view(), name='source-extras'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', SourceExtraRetrieveUpdateDestroyView.as_view(), name='source-extra'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/$', SourceVersionRetrieveUpdateDestroyView.as_view(), name='sourceversion-detail'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/children/$', SourceVersionChildListView.as_view(), {'list_children': True}, name='sourceversion-child-list'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/export/$', SourceVersionExportView.as_view(), name='sourceversion-export'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/extras/$', SourceExtrasView.as_view(), name='sourceversion-extras'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', SourceExtraRetrieveUpdateDestroyView.as_view(), name='sourceversion-extra'),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/mappings/', include('mappings.urls')),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/', include('concepts.urls')),
    url(r'^(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/processing/$', SourceVersionProcessingView.as_view(), name='sourceversion-processing'),
)
