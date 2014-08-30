from django.conf.urls import include
from django.conf.urls.defaults import patterns, url
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView, ConceptVersionsView, ConceptNameRetrieveUpdateDestroyView, ConceptNameListCreateView, ConceptDescriptionListCreateView, ConceptDescriptionRetrieveUpdateDestroyView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', ConceptCreateView.as_view(), name='concept-create'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/mappings/', include('mappings.urls')),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/names/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/versions/$', ConceptVersionsView.as_view(), name='concept-version-list'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
)

