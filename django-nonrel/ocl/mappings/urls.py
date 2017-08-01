from django.conf.urls import patterns, url
from mappings.views import MappingListView, MappingDetailView, MappingVersionDetailView, MappingVersionsListView, MappingVersionsView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', MappingListView.as_view(), name='mapping-list'),
    url(r'^(?P<mapping>[a-zA-Z0-9\-\.]+)/$', MappingDetailView.as_view(), name='mapping-detail'),
    url(r'^(?P<mapping>[a-zA-Z0-9\-\.]+)/versions/$', MappingVersionsView.as_view(), name='mapping-version-list'),
    url(r'^(?P<mapping>[a-zA-Z0-9\-\.]+)/(?P<mapping_version>[a-zA-Z0-9\-\.]+)/$', MappingVersionDetailView.as_view(), name='mappingversion-detail'),
)
