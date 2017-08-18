from django.conf.urls import patterns, url, include
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView, ConceptVersionsView, ConceptNameRetrieveUpdateDestroyView, ConceptNameListCreateView, ConceptDescriptionRetrieveUpdateDestroyView, ConceptDescriptionListCreateView, ConceptExtrasView, ConceptExtraRetrieveUpdateDestroyView, ConceptMappingsView
from mappings.views import MappingListView, MappingDetailView, MappingVersionDetailView, MappingVersionsListView
from orgs.views import OrganizationListView
from sources.views import SourceListView, SourceRetrieveUpdateDestroyView, SourceVersionRetrieveUpdateView, SourceVersionChildListView, SourceVersionListView, SourceVersionRetrieveUpdateDestroyView
from users.views import UserDetailView

from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'

extra_kwargs = {'user_is_self': True}

urlpatterns = patterns('',
    # shortcuts for the currently logged-in user
    url(r'^$', UserDetailView.as_view(), extra_kwargs, name='user-self-detail'),
    url(r'^orgs/$', OrganizationListView.as_view(), extra_kwargs, name='user-organization-list'),
    url(r'^sources/$', SourceListView.as_view(), extra_kwargs, name='user-source-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/$', SourceRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-source-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/$', ConceptCreateView.as_view(), name='concept-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/descriptions/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-description'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/names/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/versions/$', ConceptVersionsView.as_view(), name='concept-version-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/mappings/$', ConceptMappingsView.as_view(), name='concept-mapping-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/descriptions/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/extras/(?P<extra>' + CONCEPT_ID_PATTERN + ')/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/(?P<concept_version>' + NAMESPACE_PATTERN + ')/names/(?P<uuid>' + NAMESPACE_PATTERN + ')/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/mappings/$', MappingListView.as_view(), name='mapping-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/mappings/(?P<mapping>' + NAMESPACE_PATTERN + ')/versions/$', MappingVersionsListView.as_view(), name='mapping-version-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/mappings/(?P<mapping>' + NAMESPACE_PATTERN + ')/$', MappingDetailView.as_view(), name='mapping-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/mappings/(?P<mapping>' + NAMESPACE_PATTERN + ')/(?P<mapping_version>' + NAMESPACE_PATTERN + ')/$', MappingVersionDetailView.as_view(), name='mappingversion-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/versions/$', SourceVersionListView.as_view(), extra_kwargs, name='user-sourceversion-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/latest/$', SourceVersionRetrieveUpdateView.as_view(), {'user_is_self': True, 'is_latest': True}, name='user-sourceversion-latest'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/$', SourceVersionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-sourceversion-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/children/$', SourceVersionChildListView.as_view(), extra_kwargs, name='user-sourceversion-child-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/$', ConceptCreateView.as_view(), name='concept-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/mappings/$', MappingListView.as_view(), name='mapping-list'),
    url(r'^sources/(?P<source>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/mappings/(?P<mapping>' + NAMESPACE_PATTERN + ')/$', MappingListView.as_view(), name='mapping-detail'),

    url(r'^collections/', include('collection.urls')),
    # url(r'^collections/$', CollectionListView.as_view(), extra_kwargs, name='user-collection-list'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/$', CollectionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-collection-detail'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/concepts/$', ConceptReferenceListCreateView.as_view(), name='user-collection-concepts'),
    # # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/$', ConceptReferenceRetrieveUpdateDestroyView.as_view(), name='user-collection-concept'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/versions/$', CollectionVersionListView.as_view(), extra_kwargs, name='user-sourceversion-list'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/latest/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), {'user_is_self': True, 'is_latest': True}, name='user-sourceversion-latest'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-sourceversion-detail'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/children/$', CollectionVersionChildListView.as_view(), extra_kwargs, name='user-sourceversion-child-list'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/$', ConceptReferenceListCreateView.as_view(), name='concept-list'),
    # url(r'^collections/(?P<collection>' + NAMESPACE_PATTERN + ')/(?P<version>' + NAMESPACE_PATTERN + ')/concepts/(?P<concept>' + CONCEPT_ID_PATTERN + ')/$', ConceptReferenceRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
)
