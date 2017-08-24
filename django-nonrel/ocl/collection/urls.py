from django.conf.urls import patterns, url, include
from collection.feeds import CollectionFeed
from collection.views import CollectionListView, CollectionRetrieveUpdateDestroyView, CollectionVersionListView, CollectionVersionRetrieveUpdateView, CollectionVersionRetrieveUpdateDestroyView, CollectionVersionChildListView, CollectionExtrasView, CollectionExtraRetrieveUpdateDestroyView, \
    CollectionReferencesView, CollectionVersionReferenceListView, CollectionVersionExportView
from mappings.views import MappingDetailView
from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'
urlpatterns = patterns('',
    url(r'^$', CollectionListView.as_view(), name='collection-list'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/$', CollectionRetrieveUpdateDestroyView.as_view(), name='collection-detail'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/references/$', CollectionReferencesView.as_view(), name='collection-references'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/mappings/', include('mappings.urls')),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/mappings/$',MappingDetailView.as_view(),name='concept-mapping-list'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/concepts/', include('concepts.urls')),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/versions/$', CollectionVersionListView.as_view(), name='collectionversion-list'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/latest/$', CollectionVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='collectionversion-latest-detail'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/extras/$', CollectionExtrasView.as_view(), name='collection-extras'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', CollectionExtraRetrieveUpdateDestroyView.as_view(), name='collection-extra'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/concepts/atom/$', CollectionFeed()),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), name='collectionversion-detail'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/children/$', CollectionVersionChildListView.as_view(), {'list_children': True}, name='collectionversion-child-list'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/export/$', CollectionVersionExportView.as_view(), name='collectionversion-export'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/', include('concepts.urls')),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/mappings/$', include('mappings.urls')),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/references/$', CollectionVersionReferenceListView.as_view()),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/extras/$', CollectionExtrasView.as_view(), name='collectionversion-extras'),
    url(r'^(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', CollectionExtraRetrieveUpdateDestroyView.as_view(), name='collectionversion-extra'),
)
