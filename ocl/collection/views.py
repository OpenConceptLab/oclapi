import logging
from django.conf import settings
from django.db import IntegrityError

from collection.validation_messages import HEAD_OF_CONCEPT_ADDED_TO_COLLECTION, CONCEPT_ADDED_TO_COLLECTION_FMT, \
    HEAD_OF_MAPPING_ADDED_TO_COLLECTION, MAPPING_ADDED_TO_COLLECTION_FMT
from collection.models import Collection, CollectionVersion, CollectionReference, CollectionReferenceUtils
from collection.serializers import CollectionDetailSerializer, CollectionListSerializer, CollectionCreateSerializer, \
    CollectionVersionListSerializer, CollectionVersionCreateSerializer, CollectionVersionDetailSerializer, \
    CollectionVersionUpdateSerializer, \
    CollectionReferenceSerializer
from concepts.models import Concept, ConceptVersion
from mappings.models import MappingVersion
from sources.models import SourceVersion
from concepts.serializers import ConceptListSerializer
from django.http import HttpResponse, HttpResponseForbidden
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.permissions import CanViewConceptDictionary, CanEditConceptDictionary, CanViewConceptDictionaryVersion, \
    CanEditConceptDictionaryVersion, HasOwnership
from oclapi.permissions import HasAccessToVersionedObject
from oclapi.views import ResourceVersionMixin, ResourceAttributeChildMixin, ConceptDictionaryUpdateMixin, \
    ConceptDictionaryCreateMixin, ConceptDictionaryExtrasView, ConceptDictionaryExtraRetrieveUpdateDestroyView, \
    BaseAPIView
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, get_object_or_404, DestroyAPIView
from rest_framework.response import Response
from users.models import UserProfile
from orgs.models import Organization
from tasks import export_collection, add_references
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

        data = request.DATA.get('data')
        expressions = data.get('expressions', [])
        concept_expressions = data.get('concepts', [])
        mapping_expressions = data.get('mappings', [])
        cascade_mappings_flag = request.QUERY_PARAMS.get('cascade', 'none')

        cascade_mappings = self.cascade_mapping_resolver(cascade_mappings_flag)

        host_url = request.META['wsgi.url_scheme'] + '://' + request.get_host()

        adding_all = mapping_expressions == '*' or concept_expressions == '*'

        if adding_all:
            add_references.delay(
                self.serializer_class, self.request.user, data, self.parent_resource, host_url, cascade_mappings
            )

            return Response([], status=status.HTTP_202_ACCEPTED)

        (added_references, errors) = add_references(
            self.serializer_class, self.request.user, data, self.parent_resource, host_url, cascade_mappings
        )

        all_expression = expressions + concept_expressions + mapping_expressions

        added_expression = [references.expression for references in added_references]
        added_original_expression = set([references.original_expression for references in added_references] + all_expression)

        response = []

        for expression in added_original_expression:
            response_item = self.create_response_item(added_expression, errors, expression)
            if response_item:
                response.append(response_item)

        return Response(response, status=status.HTTP_200_OK)

    def create_response_item(self, added_references, errors, expression):
        adding_expression_failed = len(errors) > 0 and errors[0].has_key(expression)
        if adding_expression_failed:
            return self.create_error_message(errors, expression)
        return self.create_success_message(added_references, expression)

    def create_success_message(self, added_references, expression):
        message = self.select_update_message(expression)

        references = filter(lambda reference: reference.startswith(expression), added_references)
        if len(references) < 1:
            return

        return {
            'added': True,
            'expression': references[0],
            'message': message
        }

    def create_error_message(self, errors, expression):
        error_message = errors[0].get(expression, {})
        return {
            'added': False,
            'expression': expression,
            'message': error_message
        }

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = CollectionReferenceSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        search_query = self.request.QUERY_PARAMS.get('q', '')
        sort = self.request.QUERY_PARAMS.get('search_sort', 'ASC')

        references = Collection.objects.get(id=self.parent_resource.id).references
        references = [r for r in references if search_query.upper() in r.expression.upper()]
        return references if sort == 'ASC' else list(reversed(references))

    def destroy(self, request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        references = request.DATA.get("references")
        cascade_mappings_flag = request.DATA.get('cascade', 'none')

        if not references:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        if self.cascade_mapping_resolver(cascade_mappings_flag):
            references += self.get_related_mappings_with_version_information(cascade_mappings_flag, references)

        unreferenced_concepts, unreferenced_mappings = self.parent_resource.delete_references(references)
        delete_resources_from_collection_in_solr.delay(self.parent_resource.get_head().id, unreferenced_concepts,
                                                       unreferenced_mappings)

        return Response({'message': 'ok!'}, status=status.HTTP_200_OK)

    def get_related_mappings_with_version_information(self, cascade_mappings_flag, references):
        related_mappings = []

        for reference in references:
            if CollectionReferenceUtils.is_concept(reference):
                concept_id = CollectionReferenceUtils.get_concept_id_by_version_information(reference)
                related_mappings += Concept.objects.get(id=concept_id).get_unidirectional_mappings()

        return self.get_version_information_of_related_mappings(related_mappings)

    def get_version_information_of_related_mappings(self, related_mappings):
        related_mappings_with_version = []

        for reference in self.parent_resource.references:
            for related_mapping in related_mappings:
                if related_mapping.url in reference.expression:
                    related_mappings_with_version += [reference.expression]

        return related_mappings_with_version

    def cascade_mapping_resolver(self, cascade_mappings_flag):
        cascade_mappings_flag_resolver = {
            'none': False,
            'sourcemappings': True
        }

        return cascade_mappings_flag_resolver.get(cascade_mappings_flag.lower(), False)

    def select_update_message(self, expression):
        adding_head_version = not CollectionReference.version_specified(expression)

        expression_parts = expression.split('/')
        resource_type = expression_parts[5]

        if adding_head_version:
            return self.adding_to_head_message_by_type(resource_type)

        resource_name = expression_parts[6]
        return self.version_added_message_by_type(resource_name, self.parent_resource.name, resource_type)

    def adding_to_head_message_by_type(self, resource_type):
        if resource_type == 'concepts':
            return HEAD_OF_CONCEPT_ADDED_TO_COLLECTION
        return HEAD_OF_MAPPING_ADDED_TO_COLLECTION

    def version_added_message_by_type(self, resource_name, collection_name, resource_type):
        if resource_type == 'concepts':
            return CONCEPT_ADDED_TO_COLLECTION_FMT.format(resource_name, collection_name)
        return MAPPING_ADDED_TO_COLLECTION_FMT.format(resource_name, collection_name)


class CollectionListView(CollectionBaseView,
                         ConceptDictionaryCreateMixin,
                         ListWithHeadersMixin):
    serializer_class = CollectionCreateSerializer
    filter_backends = [CollectionSearchFilter]
    contains_uri = None
    solr_fields = {
        'collection_type': {'sortable': False, 'filterable': True},
        'name': {'sortable': True, 'filterable': False},
        'last_update': {'sortable': True, 'default': 'desc', 'filterable': False},
        'num_stars': {'sortable': True, 'filterable': False},
        'language': {'sortable': False, 'filterable': True}
    }

    def get(self, request, *args, **kwargs):
        self.serializer_class = CollectionDetailSerializer if self.is_verbose(request) else CollectionListSerializer
        self.contains_uri = request.QUERY_PARAMS.get('contains', None)
        collection_list = self.list(request, *args, **kwargs)
        return collection_list

    def get_queryset(self):
        queryset = super(CollectionListView, self).get_queryset()
        if self.contains_uri != None:
            queryset = queryset.filter(references__contains=self.contains_uri)
        return queryset

    def get_csv_rows(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()

        values = queryset.values('mnemonic', 'name', 'full_name', 'collection_type', 'description', 'default_locale',
                                 'supported_locales', 'website', 'external_id', 'updated_at', 'updated_by', 'uri')

        for value in values:
            value['Owner'] = Collection.objects.get(uri=value['uri']).parent.mnemonic
            value['Collection ID'] = value.pop('mnemonic')
            value['Collection Name'] = value.pop('name')
            value['Collection Full Name'] = value.pop('full_name')
            value['Collection Type'] = value.pop('collection_type')
            value['Description'] = value.pop('description')
            value['Default Locale'] = value.pop('default_locale')
            value['Supported Locales'] = ",".join(value.pop('supported_locales'))
            value['Website'] = value.pop('website')
            value['External ID'] = value.pop('external_id')
            value['Last Updated'] = value.pop('updated_at')
            value['Updated By'] = value.pop('updated_by')
            value['URI'] = value.pop('uri')

        values.field_names.extend(
            ['Owner', 'Collection ID', 'Collection Name', 'Collection Full Name', 'Collection Type', 'Description',
             'Default Locale', 'Supported Locales', 'Website'
                , 'External ID', 'Last Updated', 'Updated By', 'URI'])
        del values.field_names[0:12]
        return values


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
        self.serializer_class = CollectionVersionDetailSerializer if self.is_verbose(
            request) else CollectionVersionListSerializer
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
                    version = self.object
                    export_collection.delay(version.id)
                    return Response(serializer.data, status=status.HTTP_201_CREATED,
                                    headers=headers)
            except IntegrityError, e:
                result = {'error': str(e),
                          'detail': 'Collection version  \'%s\' already exist. ' % serializer.data.get('id')}
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
        self.serializer_class = CollectionVersionDetailSerializer if self.is_verbose(
            request) else CollectionVersionListSerializer
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

class CollectionVersionProcessingView(ResourceAttributeChildMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    permission_classes = (CanViewConceptDictionaryVersion,)

    def get(self, request, *args, **kwargs):
        version = self.get_object()
        logger.debug('Processing flag requested for collection version %s' % version)

        response = HttpResponse(status=200)
        response.content = version.is_processing
        return response

    def post(self, request, *args, **kwargs):
        self.permission_classes = (HasOwnership,)

        version = self.get_object()
        logger.debug('Processing flag clearance requested for collection version %s' % version)

        version.clear_processing()

        response = HttpResponse(status=200)
        return response

    def get_queryset(self):
        owner = self.get_owner(self.kwargs)
        queryset = super(CollectionVersionProcessingView, self).get_queryset()
        return queryset.filter(
            versioned_object_id=Collection.objects.get(parent_id=owner.id, mnemonic=self.kwargs['collection']).id,
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


class CollectionVersionExportView(ResourceAttributeChildMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    permission_classes = (CanViewConceptDictionaryVersion,)

    def get(self, request, *args, **kwargs):
        version = self.get_object()
        logger.debug('Export requested for collection version %s - Requesting AWS-S3 key' % version)

        if version.mnemonic == 'HEAD':
            return HttpResponse(status=405)

        key = version.get_export_key()
        url, status = None, 204

        if key:
            logger.debug('   Key retreived for collection version %s - Generating URL' % version)
            url, status = key.generate_url(60), 303
            logger.debug('   URL retreived for collection version %s - Responding to client' % version)
        else:
            logger.debug('   Key does not exist for collection version %s' % version)
            return HttpResponse(status=204)

        response = HttpResponse(status=status)
        response['Location'] = url

        # Set headers to ensure sure response is not cached by a client
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Last-Updated'] = version.last_child_update.isoformat()
        response['Last-Updated-Timezone'] = settings.TIME_ZONE
        return response

    def get_queryset(self):
        owner = self.get_owner(self.kwargs)
        queryset = super(CollectionVersionExportView, self).get_queryset()
        return queryset.filter(
            versioned_object_id=Collection.objects.get(parent_id=owner.id, mnemonic=self.kwargs['collection']).id,
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
        logger.debug('Collection Export requested for version %s (post)' % version)

        if version.mnemonic == 'HEAD':
            return HttpResponse(status=405)  # export of head version is not allowed

        status = 303
        if not version.has_export():
            status = self.handle_export_collection_version()
        else:
            response = HttpResponse(status=status)
            response['URL'] = self.resource_version_path_info + 'export/'
            return response

        return HttpResponse(status=status)

    def delete(self, request, *args, **kwargs):
        user = request.user
        userprofile = UserProfile.objects.get(mnemonic=user.username)
        version = self.get_object()

        permitted = user.is_staff or \
                    user.is_superuser or \
                    userprofile.is_admin_for(version.versioned_object)

        if not permitted:
            return HttpResponseForbidden()
        if version.has_export():
            key = version.get_export_key()
            if key:
                key.delete()
                return HttpResponse(status=200)

        return HttpResponse(status=204)

    def handle_export_collection_version(self):
        version = self.get_object()
        try:
            export_collection.delay(version.id)
            return 202
        except AlreadyQueued:
            return 409
