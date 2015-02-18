from django.conf.urls import patterns, url
from concepts.feeds import ConceptFeed
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView, ConceptVersionsView, ConceptNameRetrieveUpdateDestroyView, ConceptNameListCreateView, ConceptDescriptionListCreateView, ConceptDescriptionRetrieveUpdateDestroyView, ConceptExtrasView, ConceptExtraRetrieveUpdateDestroyView, ConceptMappingsView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', ConceptCreateView.as_view(), name='concept-create'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/atom/$', ConceptFeed()),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/extras/(?P<extra>[_a-zA-Z0-9\-\.]+)/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/names/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/mappings/$', ConceptMappingsView.as_view(), name='concept-mapping-list'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/versions/$', ConceptVersionsView.as_view(), name='concept-version-list'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
)

