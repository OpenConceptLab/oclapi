from django.conf.urls import patterns, url, include
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView, ConceptVersionsView, ConceptNameRetrieveUpdateDestroyView, ConceptNameListCreateView, ConceptDescriptionRetrieveUpdateDestroyView, ConceptDescriptionListCreateView, ConceptExtrasView, ConceptExtraRetrieveUpdateDestroyView, ConceptMappingsView
from mappings.views import MappingListView, MappingDetailView, MappingVersionDetailView, MappingVersionsListView
from orgs.views import OrganizationListView
from sources.views import SourceListView, SourceRetrieveUpdateDestroyView, SourceVersionRetrieveUpdateView, SourceVersionChildListView, SourceVersionListView, SourceVersionRetrieveUpdateDestroyView
from users.views import UserDetailView

__author__ = 'misternando'

extra_kwargs = {'user_is_self': True}

urlpatterns = patterns('',
    # shortcuts for the currently logged-in user
    url(r'^$', UserDetailView.as_view(), extra_kwargs, name='user-self-detail'),
    url(r'^orgs/$', OrganizationListView.as_view(), extra_kwargs, name='user-organization-list'),
    url(r'^sources/$', SourceListView.as_view(), extra_kwargs, name='user-source-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/$', SourceRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-source-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/$', ConceptCreateView.as_view(), name='concept-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/descriptions/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-description'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/extras/(?P<extra>[_a-zA-Z0-9\-\.]+)/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/names/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/versions/$', ConceptVersionsView.as_view(), name='concept-version-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/mappings/$', ConceptMappingsView.as_view(), name='concept-mapping-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/descriptions/$', ConceptDescriptionListCreateView.as_view(), name='concept-descriptions'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/descriptions/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptDescriptionRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/extras/$', ConceptExtrasView.as_view(), name='concept-extras'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/extras/(?P<extra>[_a-zA-Z0-9\-\.]+)/$', ConceptExtraRetrieveUpdateDestroyView.as_view(), name='concept-extra'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/names/$', ConceptNameListCreateView.as_view(), name='concept-names'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/names/(?P<uuid>[a-zA-Z0-9\-\.]+)/$', ConceptNameRetrieveUpdateDestroyView.as_view(), name='concept-name'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/mappings/$', MappingListView.as_view(), name='mapping-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/mappings/(?P<mapping>[a-zA-Z0-9\-\.]+)/versions/$', MappingVersionsListView.as_view(), name='mapping-version-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/mappings/(?P<mapping>[a-zA-Z0-9\-\.]+)/$', MappingDetailView.as_view(), name='mapping-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/mappings/(?P<mapping>[a-zA-Z0-9\-\.]+)/(?P<mapping_version>[a-zA-Z0-9\-\.]+)/$', MappingVersionDetailView.as_view(), name='mappingversion-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/versions/$', SourceVersionListView.as_view(), extra_kwargs, name='user-sourceversion-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/latest/$', SourceVersionRetrieveUpdateView.as_view(), {'user_is_self': True, 'is_latest': True}, name='user-sourceversion-latest'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/$', SourceVersionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-sourceversion-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/children/$', SourceVersionChildListView.as_view(), extra_kwargs, name='user-sourceversion-child-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/$', ConceptCreateView.as_view(), name='concept-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/mappings/$', MappingListView.as_view(), name='mapping-list'),
    url(r'^sources/(?P<source>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/mappings/(?P<mapping>[a-zA-Z0-9\-\.]+)/$', MappingListView.as_view(), name='mapping-detail'),

    url(r'^collections/', include('collection.urls')),
    # url(r'^collections/$', CollectionListView.as_view(), extra_kwargs, name='user-collection-list'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/$', CollectionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-collection-detail'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/concepts/$', ConceptReferenceListCreateView.as_view(), name='user-collection-concepts'),
    # # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptReferenceRetrieveUpdateDestroyView.as_view(), name='user-collection-concept'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/versions/$', CollectionVersionListView.as_view(), extra_kwargs, name='user-sourceversion-list'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/latest/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), {'user_is_self': True, 'is_latest': True}, name='user-sourceversion-latest'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/$', CollectionVersionRetrieveUpdateDestroyView.as_view(), extra_kwargs, name='user-sourceversion-detail'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/children/$', CollectionVersionChildListView.as_view(), extra_kwargs, name='user-sourceversion-child-list'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/$', ConceptReferenceListCreateView.as_view(), name='concept-list'),
    # url(r'^collections/(?P<collection>[a-zA-Z0-9\-\.]+)/(?P<version>[a-zA-Z0-9\-\.]+)/concepts/(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptReferenceRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
)
