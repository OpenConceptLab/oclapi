from django.conf.urls.defaults import patterns, url, include
from collection.views import CollectionListView, CollectionRetrieveUpdateDestroyView, CollectionVersionListView, CollectionVersionRetrieveUpdateView, CollectionVersionRetrieveUpdateDestroyView, CollectionVersionChildListView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', CollectionListView.as_view(), name='collection-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/$', CollectionRetrieveUpdateDestroyView.as_view(), name='collection-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/versions/$', CollectionVersionListView.as_view(), name='collectionversion-list'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/latest/$', CollectionVersionRetrieveUpdateView.as_view(), {'is_latest': True}, name='collectionversion-latest-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/concepts/', include('concepts.urls')),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), name='collectionversion-detail'),
    url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/children/$', CollectionVersionChildListView.as_view(), {'list_children': True}, name='collectionversion-child-list'),
    #url(r'^(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/', include('concepts.urls'))
)

