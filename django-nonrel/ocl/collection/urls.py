from django.conf.urls import patterns, url, include
from collection.feeds import CollectionFeed
from collection.views import CollectionListView, CollectionRetrieveUpdateDestroyView, CollectionVersionListView, CollectionVersionRetrieveUpdateView, CollectionVersionRetrieveUpdateDestroyView, CollectionVersionChildListView, CollectionExtrasView, CollectionExtraRetrieveUpdateDestroyView, \
    CollectionReferencesView, CollectionConceptListView, CollectionVersionConceptListView, CollectionMappingListView, CollectionVersionMappingListView, \
    CollectionVersionReferenceListView, CollectionVersionExportView

__author__ = 'misternando'
urlpatterns = patterns('',
    url(r'^$', CollectionListView.as_view(), name='collection-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/$', CollectionRetrieveUpdateDestroyView.as_view(), name='collection-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/references/$', CollectionReferencesView.as_view(), name='collection-references'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/concepts/$', CollectionConceptListView.as_view(), name = 'collection-concept-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/mappings/$', CollectionMappingListView.as_view(), name = 'collection-mapping-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/versions/$', CollectionVersionListView.as_view(), name='collectionversion-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/latest/$', CollectionVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='collectionversion-latest-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/extras/$', CollectionExtrasView.as_view(), name='collection-extras'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/extras/(?P<extra>[_a-zA-Z0-9\-\.]+)/$', CollectionExtraRetrieveUpdateDestroyView.as_view(), name='collection-extra'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/concepts/atom/$', CollectionFeed()),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), name='collectionversion-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/children/$', CollectionVersionChildListView.as_view(), {'list_children': True}, name='collectionversion-child-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/$', CollectionVersionConceptListView.as_view()),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/export/$', CollectionVersionExportView.as_view(), name='collectionversion-export'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/mappings/$', CollectionVersionMappingListView.as_view()),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/references/$', CollectionVersionReferenceListView.as_view()),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/extras/$', CollectionExtrasView.as_view(), name='collectionversion-extras'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/extras/(?P<extra>[_a-zA-Z0-9\-\.]+)/$', CollectionExtraRetrieveUpdateDestroyView.as_view(), name='collectionversion-extra'),
)
