from django.conf.urls import patterns, url
from concepts.feeds import ConceptFeed
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView, ConceptVersionsView, ConceptNameRetrieveUpdateDestroyView, ConceptNameListCreateView, ConceptDescriptionListCreateView, ConceptDescriptionRetrieveUpdateDestroyView, ConceptExtrasView, ConceptExtraRetrieveUpdateDestroyView, ConceptMappingsView
from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'

urlpatterns = patterns(
    '',
    url(r'^$', ConceptCreateView.as_view(), name='concept-create'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/atom/$', ConceptFeed()),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/descriptions/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/names/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/mappings/$', ConceptMappingsView.as_view(), name='concept-mapping-list'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/versions/$', ConceptVersionsView.as_view(), name='concept-version-list'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/descriptions/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/names/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
)
