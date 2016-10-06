import logging
from django.conf import settings
from django.db import IntegrityError

from collection.models import Collection, CollectionVersion, CollectionReference
from collection.serializers import CollectionDetailSerializer, CollectionListSerializer, CollectionCreateSerializer, CollectionVersionListSerializer, CollectionVersionCreateSerializer, CollectionVersionDetailSerializer, CollectionVersionUpdateSerializer, \
    CollectionReferenceSerializer
from concepts.models import Concept, ConceptVersion
from mappings.models import MappingVersion
from sources.models import SourceVersion
from concepts.serializers import ConceptListSerializer
from django.http import HttpResponse, HttpResponseForbidden
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.permissions import CanViewConceptDictionary, CanEditConceptDictionary, CanViewConceptDictionaryVersion, CanEditConceptDictionaryVersion
from oclapi.permissions import HasAccessToVersionedObject
from oclapi.views import ResourceVersionMixin, ResourceAttributeChildMixin, ConceptDictionaryUpdateMixin, ConceptDictionaryCreateMixin, ConceptDictionaryExtrasView, ConceptDictionaryExtraRetrieveUpdateDestroyView, BaseAPIView
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, get_object_or_404, DestroyAPIView
from rest_framework.response import Response
from users.models import UserProfile
from orgs.models import Organization
from tasks import export_collection
from celery_once import AlreadyQueued
from django.shortcuts import get_list_or_404
from collection.filters import CollectionSearchFilter
from tasks import update_collection_in_solr, delete_resources_from_collection_in_solr
from django.core.exceptions import ValidationError


logger = logging.getLogger('oclapi')

class CollectionBaseView():
    lookup_field = 'collection'
    pk_field = 'mnemonic'
    model = Collection
    queryset = Collection.objects.filter(is_active=True)

    def get_detail_serializer(self, obj, data=None, files=None, partial=False):
        return CollectionDetailSerializer(obj, data, files, partial)

    def get_version_detail_serializer(self, obj, data=None, files=None, partial=False):
        return CollectionVersionDetailSerializer(obj, data, files, partial)

    def get_queryset(self):
        owner = self.get_owner()
        if not self.kwargs:
            return self.queryset
        elif 'collection' in self.kwargs:
            return Collection.objects.filter(parent_id=owner.id, mnemonic=self.kwargs['collection'])
        else:
            return self.queryset.filter(parent_id=owner.id)

    def get_owner(self):
        owner = None
        if 'user' in self.kwargs:
            owner_id = self.kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in self.kwargs:
            owner_id = self.kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner


class CollectionVersionBaseView(ResourceVersionMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    queryset = CollectionVersion.objects.filter(is_active=True)
    permission_classes = (HasAccessToVersionedObject,)

class CollectionRetrieveUpdateDestroyView(CollectionBaseView,
                                          RetrieveAPIView,
                                          DestroyAPIView,
                                          ConceptDictionaryUpdateMixin):
    serializer_class = CollectionDetailSerializer

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewConceptDictionary,)
        else:
            self.permission_classes = (CanEditConceptDictionary,)
        super(CollectionRetrieveUpdateDestroyView, self).initialize(request, path_info_segment, **kwargs)


class CollectionReferencesView(CollectionBaseView,
                               RetrieveAPIView,
                               DestroyAPIView,
                               UpdateAPIView,
                               ConceptDictionaryUpdateMixin,
                               ListWithHeadersMixin
                               ):

    serializer_class = CollectionDetailSerializer

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewConceptDictionary,)
        else:
            self.permission_classes = (CanEditConceptDictionary,)
        super(CollectionReferencesView, self).initialize(request, path_info_segment, **kwargs)

    def get_level(self):
        return 1

    def update(self, request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        expressions = []
        data = request.DATA.get("data")
        concept_expressions = data.get('concepts', [])
        mapping_expressions = data.get('mappings', [])
        uri = data['uri']
        ResourceContainer = SourceVersion if uri.split('/')[3] == 'sources' else CollectionVersion

        if concept_expressions == '*':
            concepts = []
            resource_container = ResourceContainer.objects.get(uri=uri)
            concepts.extend(
                Concept.objects.filter(parent_id=resource_container.versioned_object_id)
            )
            expressions.extend(map(lambda c: c.uri, concepts))
        else:
            expressions.extend(concept_expressions)

        if mapping_expressions == '*':
            mappings = []
            resource_container = ResourceContainer.objects.get(uri=uri)
            mappings.extend(
                Mapping.objects.filter(parent_id=resource_container.versioned_object_id)
            )
            expressions.extend(map(lambda m: m.uri, mappings))
        else:
            expressions.extend(mapping_expressions)

        expressions = set(expressions)
        prev_refs = self.parent_resource.references
        created = False
        save_kwargs = {'force_update': True, 'expressions': expressions}

        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.parent_resource, data=request.DATA,
                                         files=request.FILES, partial=True)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.parent_resource = serializer.save(**save_kwargs)
            self.post_save(self.parent_resource, created=created)

        update_collection_in_solr.delay(
            serializer.object.get_head().id,
            CollectionReference.diff(serializer.object.references, prev_refs)
        )

        if 'references' in serializer.errors:
            serializer.object.save()
            return Response(serializer.errors['references'], status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=success_status_code)

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = CollectionReferenceSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        search_query = self.request.QUERY_PARAMS.get('q', '')
        sort = self.request.QUERY_PARAMS.get('search_sort', 'ASC')

        references = Collection.objects.get(id=self.parent_resource.id).references
        references = [r for r in references if search_query.upper() in r.expression.upper()]
        return references if sort == 'ASC' else list(reversed(references))

    def destroy(self,request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        references = request.DATA.get("references")

        if not references:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        unreferenced_concepts, unreferenced_mappings = self.parent_resource.delete_references(references)
        delete_resources_from_collection_in_solr.delay(self.parent_resource.get_head().id, unreferenced_concepts, unreferenced_mappings)
        return Response({'message': 'ok!'}, status=status.HTTP_200_OK)

class CollectionListView(CollectionBaseView,
                         ConceptDictionaryCreateMixin,
                         ListWithHeadersMixin):
    serializer_class = CollectionCreateSerializer
    filter_backends = [CollectionSearchFilter]
    solr_fields = {
        'collection_type': {'sortable': False, 'filterable': True},
        'name': {'sortable': True, 'filterable': False},
        'last_update': {'sortable': True, 'default': 'desc', 'filterable': False},
        'num_stars': {'sortable': True, 'filterable': False},
        'language': {'sortable': False, 'filterable': True}
    }

    def get(self, request, *args, **kwargs):
        self.serializer_class = CollectionDetailSerializer if self.is_verbose(request) else CollectionListSerializer
        return self.list(request, *args, **kwargs)

class CollectionExtrasView(ConceptDictionaryExtrasView):
    pass


class CollectionExtraRetrieveUpdateDestroyView(ConceptDictionaryExtraRetrieveUpdateDestroyView):
    concept_dictionary_version_class = CollectionVersion



class CollectionVersionListView(CollectionVersionBaseView,
                                mixins.CreateModelMixin,
                                ListWithHeadersMixin):
    processing_filter = None
    released_filter = None

    def get(self, request, *args, **kwargs):
        self.permission_classes = (CanViewConceptDictionary,)
        self.serializer_class = CollectionVersionDetailSerializer if self.is_verbose(request) else CollectionVersionListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = CollectionVersionCreateSerializer
        self.permission_classes = (CanEditConceptDictionary,)
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not self.versioned_object:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            try:
                self.object = serializer.save(force_insert=True, versioned_object=self.versioned_object)
                if serializer.is_valid():
                    self.post_save(self.object, created=True)
                    headers = self.get_success_headers(serializer.data)
                    return Response(serializer.data, status=status.HTTP_201_CREATED,
                                    headers=headers)
            except IntegrityError, e:
                result = {'error':str(e), 'detail':'Collection version  \'%s\' already exist. ' % serializer.data.get('id')}
                return Response(result, status=status.HTTP_409_CONFLICT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get_queryset(self):
        queryset = super(CollectionVersionListView, self).get_queryset()
        return queryset.order_by('-created_at')


class CollectionVersionRetrieveUpdateView(CollectionVersionBaseView, RetrieveAPIView, UpdateAPIView):
    is_latest = False

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewConceptDictionaryVersion,)
            self.serializer_class = CollectionVersionDetailSerializer
        else:
            self.permission_classes = (CanEditConceptDictionaryVersion,)
            self.serializer_class = CollectionVersionUpdateSerializer
        self.is_latest = kwargs.pop('is_latest', False)
        super(CollectionVersionRetrieveUpdateView, self).initialize(request, path_info_segment, **kwargs)

    def update(self, request, *args, **kwargs):
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
                return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self, queryset=None):
        if self.is_latest:
            # Determine the base queryset to use.
            if queryset is None:
                queryset = self.filter_queryset(self.get_queryset().filter(retired=False).order_by('-created_at'))
            else:
                pass  # Deprecation warning

            filter_kwargs = {'released': True}
            obj = get_list_or_404(queryset, **filter_kwargs)[0]

            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
            return obj
        return super(CollectionVersionRetrieveUpdateView, self).get_object(queryset)


class CollectionVersionRetrieveUpdateDestroyView(CollectionVersionRetrieveUpdateView, DestroyAPIView):

    def destroy(self, request, *args, **kwargs):
        version = self.get_object()
        version.delete()
        # below commented as per issue 170
        # if version.released:
        #     errors = {'non_field_errors' : ['Cannot deactivate a version that is currently released.  Please release another version before deactivating this one.']}
        #     return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class CollectionVersionChildListView(ResourceAttributeChildMixin, ListWithHeadersMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    permission_classes = (HasAccessToVersionedObject,)
    serializer_class = CollectionVersionListSerializer

    def get(self, request, *args, **kwargs):
        self.serializer_class = CollectionVersionDetailSerializer if self.is_verbose(request) else CollectionVersionListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(CollectionVersionChildListView, self).get_queryset()
        return queryset.filter(parent_version=self.resource_version, is_active=True)



class CollectionVersionReferenceListView(CollectionVersionBaseView,
                                       ListWithHeadersMixin):
    serializer_class = CollectionReferenceSerializer

    def get(self, request, *args, **kwargs):
        search_query = self.request.QUERY_PARAMS.get('q', '')
        sort = self.request.QUERY_PARAMS.get('search_sort', 'ASC')
        object_version = self.versioned_object
        references = [
            r for r in object_version.references
            if search_query.upper() in r.expression.upper()
        ]
        self.object_list = references if sort == 'ASC' else list(reversed(references))
        return self.list(request, *args, **kwargs)


class CollectionVersionExportView(ResourceAttributeChildMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    permission_classes = (CanViewConceptDictionaryVersion,)

    def get(self, request, *args, **kwargs):
        version = self.get_object()
        logger.debug('Export requested for collection version %s - Requesting AWS-S3 key' % version)
        key = version.get_export_key()
        url, status = None, 204

        if version.mnemonic == 'HEAD':
            return HttpResponse(status=405)

        if key:
            logger.debug('   Key retreived for collection version %s - Generating URL' % version)
            url, status = key.generate_url(60), 200
            logger.debug('   URL retreived for collection version %s - Responding to client' % version)
        else:
            logger.debug('   Key does not exist for collection version %s' % version)
            status = self.handle_export_collection_version()


        response = HttpResponse(status=status)
        response['Location'] = url

        # Set headers to ensure sure response is not cached by a client
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['lastUpdated'] = version.last_child_update.isoformat()
        response['lastUpdatedTimezone'] = settings.TIME_ZONE
        return response

    def get_queryset(self):
        owner = self.get_owner(self.kwargs)
        queryset = super(CollectionVersionExportView, self).get_queryset()
        return queryset.filter(versioned_object_id=Collection.objects.get(parent_id=owner.id, mnemonic=self.kwargs['collection']).id,
                                            mnemonic=self.kwargs['version'])
    def get_owner(self, kwargs):
        owner = None
        if 'user' in kwargs:
            owner_id = kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in kwargs:
            owner_id = kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner

    def post(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        version = self.get_object()

        if version.mnemonic == 'HEAD':
            return HttpResponse(status=405)  # export of head version is not allowed

        logger.debug('Collection Export requested for version %s (post)' % version)
        status = 204
        if not version.has_export():
            status = self.handle_export_collection_version()
        return HttpResponse(status=status)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden()
        version = self.get_object()
        if version.has_export():
            key = version.get_export_key()
            key.delete()
        return HttpResponse(status=204)

    def handle_export_collection_version(self):
        version = self.get_object()
        try:
            export_collection.delay(version.id)
            return 200
        except AlreadyQueued:
            return 204

