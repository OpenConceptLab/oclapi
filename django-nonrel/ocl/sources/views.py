import logging

from django.conf import settings
from django.db.models import Q
from django.db.models.query import EmptyQuerySet
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, get_object_or_404, DestroyAPIView
from rest_framework.response import Response
from concepts.models import ConceptVersion
from concepts.serializers import ConceptVersionDetailSerializer
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.permissions import HasAccessToVersionedObject, CanEditConceptDictionaryVersion, CanViewConceptDictionary, CanViewConceptDictionaryVersion
from oclapi.filters import HaystackSearchFilter
from oclapi.views import ResourceVersionMixin, ResourceAttributeChildMixin, ConceptDictionaryUpdateMixin, ConceptDictionaryCreateMixin, ConceptDictionaryExtrasView, ConceptDictionaryExtraRetrieveUpdateDestroyView, parse_updated_since_param
from sources.models import Source, SourceVersion
from sources.serializers import SourceCreateSerializer, SourceListSerializer, SourceDetailSerializer, SourceVersionDetailSerializer, SourceVersionListSerializer, SourceVersionCreateSerializer, SourceVersionUpdateSerializer
from tasks import export_source


INCLUDE_CONCEPTS_PARAM = 'includeConcepts'
INCLUDE_MAPPINGS_PARAM = 'includeMappings'
LIMIT_PARAM = 'limit'
INCLUDE_RETIRED_PARAM = 'includeRetired'

logger = logging.getLogger('oclapi')


class SourceBaseView():
    lookup_field = 'source'
    pk_field = 'mnemonic'
    model = Source
    permission_classes = (CanViewConceptDictionary,)
    queryset = Source.objects.filter(is_active=True)

    def get_detail_serializer(self, obj, data=None, files=None, partial=False):
        return SourceDetailSerializer(obj, data, files, partial)


class SourceRetrieveUpdateDestroyView(SourceBaseView,
                                      ConceptDictionaryUpdateMixin,
                                      RetrieveAPIView,
                                      DestroyAPIView):
    serializer_class = SourceDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        super(SourceRetrieveUpdateDestroyView, self).retrieve(request, *args, **kwargs)
        self.object = self.get_object()
        serializer = self.get_serializer(self.object)
        data = serializer.data

        source_version = None
        limit = settings.REST_FRAMEWORK.get('MAX_PAGINATE_BY', self.paginate_by)
        include_retired = False
        include_concepts = request.QUERY_PARAMS.get(INCLUDE_CONCEPTS_PARAM, False)
        include_mappings = request.QUERY_PARAMS.get(INCLUDE_MAPPINGS_PARAM, False)
        updated_since = None
        if include_concepts or include_mappings:
            source_version = SourceVersion.get_latest_version_of(self.object)
            paginate_by = self.get_paginate_by(EmptyQuerySet())
            if paginate_by:
                limit = min(limit, paginate_by)
            include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
            updated_since = parse_updated_since_param(request)

        if include_concepts:
            source_version_concepts = source_version.concepts
            queryset = ConceptVersion.objects.filter(is_active=True)
            if not include_retired:
                queryset = queryset.filter(~Q(retired=True))
            if updated_since:
                queryset = queryset.filter(updated_at__gte=updated_since)
            queryset = queryset.filter(id__in=source_version_concepts)
            queryset = queryset[0:limit]
            serializer = ConceptVersionDetailSerializer(queryset, many=True)
            data['concepts'] = serializer.data

        if include_mappings:
            all_children = source_version.mappings
            queryset = Mapping.objects.filter(is_active=True)
            if not include_retired:
                queryset = queryset.filter(~Q(retired=True))
            queryset = queryset.filter(id__in=all_children)
            if updated_since:
                queryset = queryset.filter(updated_at__gte=updated_since)
            queryset = queryset[0:limit]
            serializer = MappingDetailSerializer(queryset, many=True)
            data['mappings'] = serializer.data

        return Response(data)


class SourceListView(SourceBaseView,
                     ConceptDictionaryCreateMixin,
                     ListWithHeadersMixin):
    serializer_class = SourceCreateSerializer
    filter_backends = [HaystackSearchFilter]
    solr_fields = {
        'sourceType': {'sortable': False, 'filterable': True, 'facet': True},
        'name': {'sortable': True, 'filterable': False},
        'lastUpdate': {'sortable': True, 'filterable': False},
        'locale': {'sortable': False, 'filterable': True, 'facet': True},
        'owner': {'sortable': False, 'filterable': True, 'facet': True},
        'ownerType': {'sortable': False, 'filterable': True, 'facet': True},
    }

    def get(self, request, *args, **kwargs):
        self.serializer_class = SourceDetailSerializer if self.is_verbose(request) else SourceListSerializer
        return self.list(request, *args, **kwargs)


class SourceExtrasView(ConceptDictionaryExtrasView):
    pass


class SourceExtraRetrieveUpdateDestroyView(ConceptDictionaryExtraRetrieveUpdateDestroyView):
    concept_dictionary_version_class = SourceVersion


class SourceVersionBaseView(ResourceVersionMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = SourceVersion
    queryset = SourceVersion.objects.filter(is_active=True)
    permission_classes = (HasAccessToVersionedObject,)


class SourceVersionListView(SourceVersionBaseView,
                            mixins.CreateModelMixin,
                            ListWithHeadersMixin):

    def get(self, request, *args, **kwargs):
        self.permission_classes = (CanViewConceptDictionaryVersion,)
        self.serializer_class = SourceVersionDetailSerializer if self.is_verbose(request) else SourceVersionListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = SourceVersionCreateSerializer
        self.permission_classes = (CanEditConceptDictionaryVersion,)
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not self.versioned_object:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, versioned_object=self.versioned_object)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                serializer = SourceVersionDetailSerializer(self.object, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SourceVersionRetrieveUpdateView(SourceVersionBaseView, RetrieveAPIView, UpdateAPIView):
    is_latest = False
    permission_classes = (CanViewConceptDictionaryVersion,)
    serializer_class = SourceVersionDetailSerializer

    def initialize(self, request, path_info_segment, **kwargs):
        self.is_latest = kwargs.pop('is_latest', False)
        super(SourceVersionRetrieveUpdateView, self).initialize(request, path_info_segment, **kwargs)

    def update(self, request, *args, **kwargs):
        self.permission_classes = (CanEditConceptDictionaryVersion,)
        self.serializer_class = SourceVersionUpdateSerializer
        if not self.versioned_object:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        self.object = self.get_object()
        created = False
        save_kwargs = {'force_update': True, 'versioned_object': self.versioned_object}
        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=True)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=created)
                serializer = SourceVersionDetailSerializer(self.object, context={'request': request})
                return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self, queryset=None):
        if self.is_latest:
            # Determine the base queryset to use.
            if queryset is None:
                queryset = self.filter_queryset(self.get_queryset())
            else:
                pass  # Deprecation warning

            filter_kwargs = {'released': True}
            obj = get_object_or_404(queryset, **filter_kwargs)

            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
            return obj
        return super(SourceVersionRetrieveUpdateView, self).get_object(queryset)


class SourceVersionRetrieveUpdateDestroyView(SourceVersionRetrieveUpdateView, DestroyAPIView):

    def destroy(self, request, *args, **kwargs):
        self.permission_classes = (CanEditConceptDictionaryVersion,)
        version = self.get_object()
        if version.released:
            errors = {'non_field_errors' : ['Cannot deactivate a version that is currently released.  Please release another version before deactivating this one.']}
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return super(SourceVersionRetrieveUpdateDestroyView, self).destroy(request, *args, **kwargs)


class SourceVersionChildListView(ResourceAttributeChildMixin, ListWithHeadersMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = SourceVersion
    permission_classes = (HasAccessToVersionedObject,)

    def get(self, request, *args, **kwargs):
        self.serializer_class = SourceVersionDetailSerializer if self.is_verbose(request) else SourceVersionListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(SourceVersionChildListView, self).get_queryset()
        return queryset.filter(parent_version=self.resource_version, is_active=True)


class SourceVersionExportView(ResourceAttributeChildMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = SourceVersion
    permission_classes = (CanViewConceptDictionaryVersion,)

    def get(self, request, *args, **kwargs):
        version = self.get_object()
        logger.debug('Source Export requested for version %s' % version)
        key = version.get_export_key()
        url, status = None, 204
        if key:
            url, status = key.generate_url(60), 200
        else:
            export_source.delay(version.id)
        response = HttpResponse(status=status)
        response['exportURL'] = url
        return response

    def post(self, request, *args, **kwargs):
        version = self.get_object()
        logger.debug('Source Export requested for version %s (post)' % version)
        if version.has_export():
            return HttpResponse(status=204)
        else:
            export_source.delay(version.id)
            return HttpResponse(status=200)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden()
        version = self.get_object()
        if version.has_export():
            key = version.get_export_key()
            key.delete()
        return HttpResponse(status=204)

