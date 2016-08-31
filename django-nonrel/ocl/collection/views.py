from collection.models import Collection, CollectionVersion
from collection.serializers import CollectionDetailSerializer, CollectionListSerializer, CollectionCreateSerializer, CollectionVersionListSerializer, CollectionVersionCreateSerializer, CollectionVersionDetailSerializer, CollectionVersionUpdateSerializer
from concepts.models import Concept
from concepts.serializers import ConceptListSerializer
from django.http import HttpResponse
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin
from oclapi.permissions import CanViewConceptDictionary, CanEditConceptDictionary, CanViewConceptDictionaryVersion, CanEditConceptDictionaryVersion
from oclapi.permissions import HasAccessToVersionedObject
from oclapi.views import ResourceVersionMixin, ResourceAttributeChildMixin, ConceptDictionaryUpdateMixin, ConceptDictionaryCreateMixin, ConceptDictionaryExtrasView, ConceptDictionaryExtraRetrieveUpdateDestroyView, BaseAPIView
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, get_object_or_404, DestroyAPIView
from rest_framework.response import Response
from users.models import UserProfile
from orgs.models import Organization
from django.db import IntegrityError

class CollectionBaseView():
    lookup_field = 'collection'
    pk_field = 'mnemonic'
    model = Collection
    queryset = Collection.objects.filter(is_active=True)

    def get_detail_serializer(self, obj, data=None, files=None, partial=False):
        return CollectionDetailSerializer(obj, data, files, partial)

    def get_version_detail_serializer(self, obj, data=None, files=None, partial=False):
        return CollectionVersionDetailSerializer(obj, data, files, partial)

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
                               ConceptDictionaryUpdateMixin
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

        self.object = self.get_object(self.queryset)
        created = False
        save_kwargs = {'force_update': True, 'expression': request.DATA.get("expression")}

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

    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object(self.queryset)
        serializer = self.get_serializer(self.object)
        success_status_code = status.HTTP_200_OK
        return Response(serializer.data, status=success_status_code)

    def destroy(self,request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        owner = self.get_owner(kwargs)
        references = request.QUERY_PARAMS.getlist("references")

        if not owner or not references:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        collection = Collection.objects.get(mnemonic=self.parent_resource, parent_id=owner.id)
        collection.delete_references(references)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_owner(self, kwargs):
        owner = None
        if 'user' in kwargs:
            owner_id = kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in kwargs:
            owner_id = kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner

class CollectionListView(CollectionBaseView,
                         ConceptDictionaryCreateMixin,
                         ListWithHeadersMixin):
    serializer_class = CollectionCreateSerializer
    filter_backends = [HaystackSearchFilter]
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
            self.object = serializer.save(force_insert=True, versioned_object=self.versioned_object)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

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
                queryset = self.filter_queryset(self.get_queryset())
            else:
                pass  # Deprecation warning

            filter_kwargs = {'released': True}
            obj = get_object_or_404(queryset, **filter_kwargs)

            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
            return obj
        return super(CollectionVersionRetrieveUpdateView, self).get_object(queryset)


class CollectionVersionRetrieveUpdateDestroyView(CollectionVersionRetrieveUpdateView, DestroyAPIView):

    def destroy(self, request, *args, **kwargs):
        version = self.get_object()
        if version.released:
            errors = {'non_field_errors' : ['Cannot deactivate a version that is currently released.  Please release another version before deactivating this one.']}
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return super(CollectionVersionRetrieveUpdateDestroyView, self).destroy(request, *args, **kwargs)


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


class CollectionConceptListView(CollectionBaseView,
                                BaseAPIView,
                                ListWithHeadersMixin):
    serializer_class = ConceptListSerializer

    def get(self, request, *args, **kwargs):
        collection = self.get_object()
        object_version = CollectionVersion.get_head(collection.id)
        self.object_list = Concept.objects.filter(id__in=object_version.concepts)
        return self.list(request, *args, **kwargs)


class CollectionVersionConceptListView(CollectionVersionBaseView,
                                       ListWithHeadersMixin):
    serializer_class = ConceptListSerializer

    def get(self, request, *args, **kwargs):
        object_version = self.versioned_object
        self.object_list = Concept.objects.filter(id__in=object_version.concepts)
        return self.list(request, *args, **kwargs)


class CollectionMappingListView(CollectionBaseView,
                                BaseAPIView,
                                ListWithHeadersMixin):
    serializer_class = MappingDetailSerializer
    def get(self, request, *args, **kwargs):
        collection = self.get_object()
        object_version = CollectionVersion.get_head(collection.id)

        self.object_list = Mapping.objects.filter(id__in=object_version.mappings)
        return self.list(request, *args, **kwargs)


class CollectionVersionMappingListView(CollectionVersionBaseView,
                                       ListWithHeadersMixin):
    serializer_class = MappingDetailSerializer

    def get(self, request, *args, **kwargs):
        object_version = self.versioned_object
        self.object_list = Mapping.objects.filter(id__in=object_version.mappings)
        return self.list(request, *args, **kwargs)


