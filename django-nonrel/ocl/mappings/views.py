from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response
from concepts.permissions import CanEditParentDictionary, CanViewParentDictionary
from mappings.filters import PublicMappingsSearchFilter, SourceRestrictedMappingsFilter, CollectionRestrictedMappingFilter
from mappings.models import Mapping, MappingVersion
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer, MappingDetailSerializer, MappingListSerializer, \
    MappingVersionDetailSerializer, MappingVersionListSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.models import ACCESS_TYPE_NONE
from oclapi.views import ConceptDictionaryMixin, BaseAPIView, parse_updated_since_param, VersionedResourceChildMixin
from sources.models import SourceVersion
from orgs.models import Organization
from users.models import UserProfile

INCLUDE_RETIRED_PARAM = 'includeRetired'
LIMIT_PARAM = 'limit'


class MappingBaseView(ConceptDictionaryMixin):
    lookup_field = 'mapping'
    pk_field = 'id'
    model = Mapping
    child_list_attribute = 'mappings'
    include_retired = False
    permission_classes = (CanViewParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        super(MappingBaseView, self).initialize(request, path_info_segment, **kwargs)
        if self.parent_resource:
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource_version = self.parent_resource
                self.parent_resource = self.parent_resource.versioned_object
            else:
                self.parent_resource_version = self.parent_resource.get_head()

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        owner_is_self = self.parent_resource and self.userprofile and self.parent_resource.owner == self.userprofile
        if self.parent_resource:
            queryset = queryset.filter(parent_id=self.parent_resource.id)
        if not(self.user.is_staff or owner_is_self):
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
        return queryset

class MappingVersionBaseView(ConceptDictionaryMixin):
    lookup_field = 'mapping_version'
    model = MappingVersion
    include_retired = False
    permission_classes = (CanViewParentDictionary,)
    queryset = MappingVersion.objects.filter(is_active=True)
    def initialize(self, request, path_info_segment, **kwargs):
        super(MappingVersionBaseView, self).initialize(request, path_info_segment, **kwargs)

    def get_queryset(self):
        queryset = MappingVersion.objects.filter(is_active=True, versioned_object_id=self.kwargs.get('mapping'))
        return queryset


class MappingDetailView(MappingBaseView, RetrieveAPIView, UpdateAPIView, DestroyAPIView):
    serializer_class = MappingDetailSerializer

    def destroy(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        obj = self.get_object()
        Mapping.retire(obj, self.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        self.serializer_class = MappingUpdateSerializer
        partial = True
        self.object = self.get_object()

        created = False
        save_kwargs = {'force_update': True}
        if 'update_comment' in request.DATA:
            save_kwargs =  {'force_update':True, 'update_comment': request.DATA.get('update_comment')}
        else:
            save_kwargs = {'force_update': True}
        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if serializer.is_valid():
            try:
                self.pre_save(serializer.object)
            except ValidationError as e:
                return Response(e.messages, status=status.HTTP_400_BAD_REQUEST)
            self.object = serializer.save(**save_kwargs)
            self.post_save(self.object, created=created)
            serializer = MappingDetailSerializer(self.object, context={'request': request})
            return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MappingVersionMixin():
    lookup_field = 'mapping_version'
    pk_field = 'mnemonic'
    model = MappingVersion
    parent_resource_version_model = SourceVersion
    permission_classes = (CanViewParentDictionary,)
    child_list_attribute = 'mappings'


class MappingVersionsListView(MappingVersionMixin, VersionedResourceChildMixin,
                              ListWithHeadersMixin):
    serializer_class = MappingVersionListSerializer
    solr_fields = {
        'lastUpdate': {'sortable': True, 'filterable': False, 'facet': False},
        'concept': {'sortable': False, 'filterable': True, 'facet': False},
        'fromConcept': {'sortable': False, 'filterable': True, 'facet': False},
        'toConcept': {'sortable': False, 'filterable': True, 'facet': False},
        'retired': {'sortable': False, 'filterable': True, 'facet': True},
        'mapType': {'sortable': False, 'filterable': True, 'facet': True},
        'source': {'sortable': False, 'filterable': True, 'facet': True},
        'collection': {'sortable': False, 'filterable': True, 'facet': True},
        'owner': {'sortable': False, 'filterable': True, 'facet': True},
        'ownerType': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
    }

    def get(self, request, *args, **kwargs):
        self.filter_backends = [CollectionRestrictedMappingFilter] if 'collection' in kwargs else [SourceRestrictedMappingsFilter]
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.updated_since = parse_updated_since_param(request)
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        if ('collection' in self.kwargs and 'version' not in self.kwargs) or ('collection' in self.kwargs and 'version' in self.kwargs and self.kwargs['version'] == 'HEAD'):
            all_children = getattr(self.parent_resource_version, self.child_list_attribute) or []
            queryset = super(ConceptDictionaryMixin, self).get_queryset()
            queryset = queryset.filter(versioned_object_id__in=all_children, is_latest_version=True)
        else:
            queryset = super(MappingVersionsListView, self).get_queryset()

        queryset = queryset.filter(is_active=True)
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        return queryset

    def get_owner(self):
        owner = None
        if 'user' in self.kwargs:
            owner_id = self.kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in self.kwargs:
            owner_id = self.kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner


class MappingVersionsView(ConceptDictionaryMixin, ListWithHeadersMixin):
    serializer_class = MappingVersionListSerializer
    permission_classes = (CanViewParentDictionary,)

    def get(self, request, *args, **kwargs):
        self.serializer_class = MappingVersionDetailSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return MappingVersion.objects.filter(versioned_object_id=self.parent_resource.id, is_active=True)


class MappingVersionDetailView(MappingVersionBaseView, RetrieveAPIView):
    serializer_class = MappingVersionDetailSerializer
    def initialize(self, request, path_info_segment, **kwargs):
        super(MappingVersionDetailView, self).initialize(request, path_info_segment, **kwargs)

    def get_level(self):
        return 1

class MappingListView(MappingBaseView,
                      ListAPIView,
                      CreateAPIView,
                      ListWithHeadersMixin,
                      mixins.CreateModelMixin):
    queryset = Mapping.objects.filter(is_active=True)
    serializer_class = MappingCreateSerializer

    def get(self, request, *args, **kwargs):
        delegate_view = MappingVersionsListView.as_view()
        return delegate_view(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            save_kwargs = {
                'force_insert': True,
                'parent_resource': self.parent_resource,
            }
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                serializer = MappingDetailSerializer(self.object, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        #return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'errors' : (('' if k == '__all__' else k +' : ')+ v[0]) for k, v in serializer.errors.items()}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        return queryset


    def get_owner(self):
        owner = None
        if 'user' in self.kwargs:
            owner_id = self.kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in self.kwargs:
            owner_id = self.kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner


class MappingListAllView(BaseAPIView, ListWithHeadersMixin):
    model = MappingVersion
    filter_backends = [PublicMappingsSearchFilter,]
    permission_classes = (CanEditParentDictionary,)
    queryset = MappingVersion.objects.filter(is_active=True)
    solr_fields = {
        'lastUpdate': {'sortable': True, 'filterable': False, 'facet': False},
        'concept': {'sortable': False, 'filterable': True, 'facet': False},
        'fromConcept': {'sortable': False, 'filterable': True, 'facet': False},
        'toConcept': {'sortable': False, 'filterable': True, 'facet': False},
        'retired': {'sortable': False, 'filterable': True, 'facet': True},
        'mapType': {'sortable': False, 'filterable': True, 'facet': True},
        'source': {'sortable': False, 'filterable': True, 'facet': True},
        'owner': {'sortable': False, 'filterable': True, 'facet': True},
        'ownerType': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptSource': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptOwner': {'sortable': False, 'filterable': True, 'facet': True},
        'conceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
        'fromConceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
        'toConceptOwnerType': {'sortable': False, 'filterable': True, 'facet': True},
    }
    include_retired = False
    default_filters = {'is_active': True, 'is_latest_version': True}

    def get(self, request, *args, **kwargs):
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = MappingVersionDetailSerializer if self.is_verbose(request) else MappingVersionListSerializer
        self.limit = request.QUERY_PARAMS.get(LIMIT_PARAM, 25)
        return self.list(request, *args, **kwargs)

    def get_csv_rows(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()


        values = queryset.values('map_type','versioned_object_id','uri')


        for value in values:
            mapping = Mapping.objects.get(id=value.pop('versioned_object_id'))
            value['From Concept Owner'] = mapping.from_source_owner
            value['From Concept Source'] = mapping.from_source_name
            value['From Concept Code'] = mapping.from_concept_code
            value['From Concept Name'] = mapping.from_concept_name
            value['Map Type'] = value.pop('map_type')
            value['To Concept Owner'] = mapping.to_source_owner
            value['To Concept Source'] = mapping.to_source_name
            value['To Concept Code'] = mapping.get_to_concept_code()
            value['To Concept Name'] = mapping.get_to_concept_name()
            value['Internal/External'] = 'Internal' if mapping.to_concept_url else 'External'
            value['Retired'] = mapping.retired
            value['External ID'] = mapping.external_id
            value['Last Updated'] = mapping.updated_at
            value['Updated By'] = mapping.updated_by
            value['Mapping Owner'] = mapping.owner
            value['Mapping Source'] = mapping.source
            value['URI'] = value.pop('uri')

        values.field_names.extend(['From Concept Owner','From Concept Source','From Concept Code','From Concept Name','Map Type','To Concept Owner',
                                   'To Concept Source','To Concept Code','To Concept Name','Internal/External','Retired','External ID','Last Updated','Updated By','Mapping Owner','Mapping Source','URI'])
        del values.field_names[0:3]
        return values

    def get_queryset(self):
        queryset = super(MappingListAllView, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if not self.request.user.is_staff:
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
        return queryset[0:self.limit]
