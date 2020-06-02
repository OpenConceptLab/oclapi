from django.conf.urls import patterns, url
from mappings.views import MappingListView, MappingDetailView, MappingVersionDetailView, MappingVersionsListView, MappingVersionsView
from oclapi.models import NAMESPACE_PATTERN

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', MappingListView.as_view(), name='mapping-list'),
    url(r'^(?P<mapping>' + NAMESPACE_PATTERN + ')/$', MappingDetailView.as_view(), name='mapping-detail'),
    url(r'^(?P<mapping>' + NAMESPACE_PATTERN + ')/versions/$', MappingVersionsView.as_view(), name='mapping-version-list'),
    url(r'^(?P<mapping>' + NAMESPACE_PATTERN + ')/(?P<mapping_version>' + NAMESPACE_PATTERN + ')/$', MappingVersionDetailView.as_view(), name='mappingversion-detail'),
)
