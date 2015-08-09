from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response
from concepts.permissions import CanEditParentDictionary, CanViewParentDictionary
from mappings.filters import PublicMappingsSearchFilter, SourceRestrictedMappingsFilter
from mappings.models import Mapping
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer, MappingDetailSerializer, MappingListSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.models import ACCESS_TYPE_NONE
from oclapi.views import ConceptDictionaryMixin, BaseAPIView
from sources.models import SourceVersion

INCLUDE_RETIRED_PARAM = 'includeRetired'


class MappingBaseView(ConceptDictionaryMixin):
    lookup_field = 'mapping'
    pk_field = 'id'
    model = Mapping
    child_list_attribute = 'mappings'
    include_retired = False
    permission_classes = (CanViewParentDictionary,)
    parent_resource_version = None
    parent_resource_version_model = SourceVersion
    child_list_attribute = 'mappings'

    def initialize(self, request, path_info_segment, **kwargs):
        super(MappingBaseView, self).initialize(request, path_info_segment, **kwargs)
        if self.parent_resource:
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource_version = self.parent_resource
                self.parent_resource = self.parent_resource.versioned_object
            else:
                self.parent_resource_version = SourceVersion.get_latest_version_of(self.parent_resource)

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        owner_is_self = self.parent_resource and self.userprofile and self.parent_resource.owner == self.userprofile
        if self.parent_resource:
            queryset = queryset.filter(parent_id=self.parent_resource.id)
        if not(self.user.is_staff or owner_is_self):
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
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


class MappingListView(MappingBaseView,
                      ListAPIView,
                      CreateAPIView,
                      ListWithHeadersMixin,
                      mixins.CreateModelMixin):
    queryset = Mapping.objects.filter(is_active=True)
    serializer_class = MappingCreateSerializer
    solr_fields = {}
    filter_backends = [SourceRestrictedMappingsFilter,]
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

    def get(self, request, *args, **kwargs):
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = MappingDetailSerializer if self.is_verbose(request) else MappingListSerializer
        return super(MappingListView, self).get(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, parent_resource=self.parent_resource)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                serializer = MappingDetailSerializer(self.object, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        return queryset


class MappingListAllView(BaseAPIView, ListWithHeadersMixin):
    model = Mapping
    filter_backends = [PublicMappingsSearchFilter,]
    queryset = Mapping.objects.filter(is_active=True)
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

    def get(self, request, *args, **kwargs):
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = MappingDetailSerializer if self.is_verbose(request) else MappingListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(MappingListAllView, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if not self.request.user.is_staff:
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
        return queryset
