import dateutil.parser
from django.db.models import Q
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, get_object_or_404, UpdateAPIView, DestroyAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, ListCreateAPIView, ListAPIView
from rest_framework.response import Response
from concepts.filters import LimitSourceVersionFilter
from concepts.models import Concept, ConceptVersion, ConceptReference, LocalizedText
from concepts.permissions import CanViewParentDictionary, CanEditParentDictionary
from concepts.serializers import ConceptDetailSerializer, ConceptVersionListSerializer, ConceptVersionDetailSerializer, ConceptVersionUpdateSerializer, ConceptReferenceCreateSerializer, ConceptReferenceDetailSerializer, ConceptVersionsSerializer, ConceptNameSerializer, ConceptDescriptionSerializer, ReferencesToVersionsSerializer
from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin
from oclapi.models import ACCESS_TYPE_NONE, ResourceVersionModel
from oclapi.views import ConceptDictionaryMixin, VersionedResourceChildMixin, BaseAPIView, ChildResourceMixin
from sources.models import SourceVersion

UPDATED_SINCE_PARAM = 'updated_since'
INCLUDE_RETIRED_PARAM = 'include_retired'


def parse_updated_since_param(request):
    updated_since = request.QUERY_PARAMS.get(UPDATED_SINCE_PARAM)
    if updated_since:
        try:
            return dateutil.parser.parse(updated_since)
        except ValueError: pass
    return None


class ConceptBaseView(ChildResourceMixin):
    lookup_field = 'concept'
    pk_field = 'mnemonic'
    model = Concept
    permission_classes = (CanEditParentDictionary,)
    child_list_attribute = 'concepts'

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method == 'GET':
            self.permission_classes = (CanViewParentDictionary,)
        super(ConceptBaseView, self).initialize(request, path_info_segment, **kwargs)


class ConceptRetrieveUpdateDestroyView(ConceptBaseView, RetrieveAPIView, UpdateAPIView, DestroyAPIView):
    serializer_class = ConceptDetailSerializer

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            self.kwargs = kwargs
            self.request = self.initialize_request(request, *args, **kwargs)
            self.initial(self.request, *args, **kwargs)
            concept = self.get_object()
            kwargs.update({'versioned_object': concept})
            delegate_view = ConceptVersionRetrieveView.as_view()
            return delegate_view(request, *args, **kwargs)
        return super(ConceptRetrieveUpdateDestroyView, self).dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if hasattr(self.parent_resource, 'versioned_object'):
            parent_versioned_object = self.parent_resource.versioned_object
            if self.parent_resource != type(self.parent_resource).get_latest_version_of(parent_versioned_object):
                return Response({'non_field_errors': 'Parent version is not the latest.  Cannot update concept.'}, status=status.HTTP_400_BAD_REQUEST)

        self.serializer_class = ConceptVersionUpdateSerializer
        partial = kwargs.pop('partial', True)
        self.object = self.get_object_or_none()

        if self.object is None:
            return Response({'non_field_errors': 'Could not find concept to update'}, status=status.HTTP_404_NOT_FOUND)
        else:
            latest_version = ConceptVersion.get_latest_version_of(self.object)
            self.object = latest_version.clone()
            save_kwargs = {'force_update': False}
            success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                serializer = ConceptVersionDetailSerializer(self.object)
                return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        concept = self.get_object_or_none()
        if concept is None:
            return Response({'non_field_errors': 'Could not find concept to retire'}, status=status.HTTP_404_NOT_FOUND)
        Concept.retire(concept)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConceptVersionListAllView(BaseAPIView, ListWithHeadersMixin):
    model = ConceptVersion
    permission_classes = (CanViewParentDictionary,)
    filter_backends = [HaystackSearchFilter]
    queryset = ConceptVersion.objects.filter(is_active=True)
    solr_fields = {
        'name': {'sortable': True, 'filterable': False},
        'last_update': {'sortable': True, 'default': 'desc', 'filterable': False},
        'num_stars': {'sortable': True, 'filterable': False},
        'concept_class': {'sortable': False, 'filterable': True},
        'datatype': {'sortable': False, 'filterable': True},
        'locale': {'sortable': False, 'filterable': True},
    }
    updated_since = None
    include_retired = False

    def get(self, request, *args, **kwargs):
        self.updated_since = parse_updated_since_param(request)
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(ConceptVersionListAllView, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        queryset = queryset.filter(is_latest_version=True)
        if not self.request.user.is_staff:
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
        return queryset


class ConceptCreateView(ConceptBaseView,
                        mixins.CreateModelMixin):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            delegate_view = ConceptVersionListView.as_view()
            return delegate_view(request, *args, **kwargs)
        return super(ConceptCreateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = ConceptDetailSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            save_kwargs = {
                'force_insert': True,
                'owner': request.user,
                'parent_resource': self.parent_resource,
                'child_list_attribute': self.child_list_attribute
            }
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                latest_version = ConceptVersion.get_latest_version_of(self.object)
                serializer = ConceptVersionDetailSerializer(latest_version)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConceptVersionsView(ConceptDictionaryMixin, ListWithHeadersMixin):
    serializer_class = ConceptVersionListSerializer
    permission_classes = (CanViewParentDictionary,)

    def get(self, request, *args, **kwargs):
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionsSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ConceptVersion.objects.filter(versioned_object_id=self.parent_resource.id, is_active=True)


class ConceptVersionBaseView(VersionedResourceChildMixin):
    lookup_field = 'concept_version'
    pk_field = 'mnemonic'
    model = ConceptVersion
    parent_resource_version_model = SourceVersion
    permission_classes = (CanEditParentDictionary,)
    child_list_attribute = 'concepts'


class ConceptVersionListView(ConceptVersionBaseView, ListWithHeadersMixin):
    serializer_class = ConceptVersionListSerializer
    permission_classes = (CanViewParentDictionary,)
    filter_backends = [LimitSourceVersionFilter,]
    solr_fields = {
        'name': {'sortable': True, 'filterable': False},
        'last_update': {'sortable': True, 'default': 'desc', 'filterable': False},
        'num_stars': {'sortable': True, 'filterable': False},
        'concept_class': {'sortable': False, 'filterable': True},
        'datatype': {'sortable': False, 'filterable': True},
        'locale': {'sortable': False, 'filterable': True},
    }
    updated_since = None
    include_retired = False

    def get(self, request, *args, **kwargs):
        self.updated_since = parse_updated_since_param(request)
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(ConceptVersionListView, self).get_queryset()
        queryset = queryset.filter(is_active=True)
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        return queryset


class ConceptVersionRetrieveView(ConceptVersionBaseView, RetrieveAPIView):
    serializer_class = ConceptVersionDetailSerializer
    permission_classes = (CanViewParentDictionary,)
    versioned_object = None

    def initialize(self, request, path_info_segment, **kwargs):
        self.versioned_object = kwargs.pop('versioned_object', None)
        super(ConceptVersionRetrieveView, self).initialize(request, path_info_segment, **kwargs)

    def get_object(self, queryset=None):
        if self.versioned_object:
            queryset = self.get_queryset()
            filter_kwargs = {'versioned_object_id': self.versioned_object.id}
            return get_object_or_404(queryset, **filter_kwargs)
        return super(ConceptVersionRetrieveView, self).get_object()


class ConceptExtrasView(ConceptBaseView, ListAPIView):
    permission_classes = (CanViewParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=1)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)

    def list(self, request, *args, **kwargs):
        extras = self.parent_resource_version.extras or {}
        return Response(extras)


class ConceptExtraRetrieveUpdateDestroyView(ConceptBaseView, VersionedResourceChildMixin, RetrieveUpdateDestroyAPIView):

    def initialize(self, request, path_info_segment, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewParentDictionary,)
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=2)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)
        self.key = kwargs.get('extra')
        self.parent_resource_version = self.parent_resource_version.clone()
        self.extras = self.parent_resource_version.extras

    def retrieve(self, request, *args, **kwargs):
        if self.key in self.extras:
            return Response({self.key: self.extras[self.key]})
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        value = request.DATA.get(self.key)
        if not value:
            return Response(['Must specify %s param in body.' % self.key], status=status.HTTP_400_BAD_REQUEST)

        self.extras[self.key] = value
        self.parent_resource_version.update_comment = 'Updated extras: %s=%s.' % (self.key, value)
        ConceptVersion.persist_clone(self.parent_resource_version)
        return Response({self.key: self.extras[self.key]})

    def delete(self, request, *args, **kwargs):
        if self.key in self.extras:
            del self.extras[self.key]
            self.parent_resource_version.update_comment = 'Deleted extra %s.' % self.key
            ConceptVersion.persist_clone(self.parent_resource_version)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Not found."}, status.HTTP_404_NOT_FOUND)


class ConceptLabelListCreateView(ConceptBaseView, VersionedResourceChildMixin, ListWithHeadersMixin, ListCreateAPIView):
    model = LocalizedText
    parent_list_attribute = None
    permission_classes = (CanEditParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewParentDictionary,)
        super(ConceptLabelListCreateView, self).initialize(request, path_info_segment, **kwargs)

    def get_queryset(self):
        return getattr(self.parent_resource_version, self.parent_list_attribute)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            new_version = self.parent_resource_version.clone()
            labels = getattr(new_version, self.parent_list_attribute)
            labels.append(serializer.object)
            new_version.update_comment = 'Added to %s: %s.' % (self.parent_list_attribute, serializer.object.name)
            ConceptVersion.persist_clone(new_version)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConceptNameListCreateView(ConceptLabelListCreateView):
    serializer_class = ConceptNameSerializer
    parent_list_attribute = 'names'


class ConceptDescriptionListCreateView(ConceptLabelListCreateView):
    serializer_class = ConceptDescriptionSerializer
    parent_list_attribute = 'descriptions'


class ConceptLabelRetrieveUpdateDestroyView(ConceptBaseView, VersionedResourceChildMixin, RetrieveUpdateDestroyAPIView):
    model = LocalizedText
    parent_list_attribute = None
    permission_classes = (CanEditParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewParentDictionary,)
        super(ConceptLabelRetrieveUpdateDestroyView, self).initialize(request, path_info_segment, **kwargs)

    def get_object(self, queryset=None):
        uuid = self.kwargs.get('uuid')
        self.parent_resource_version = self.parent_resource_version.clone()
        labels = getattr(self.parent_resource_version, self.parent_list_attribute)
        for label in labels:
            if uuid == unicode(label.uuid):
                return label
        raise Http404()

    def update(self, request, *args, **kwargs):
        partial = True
        self.object = self.get_object()
        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if serializer.is_valid():
            self.parent_resource_version.update_comment = 'Updated %s in %s.' % (self.object.name, self.parent_list_attribute)
            ConceptVersion.persist_clone(self.parent_resource_version)
            return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        index_to_remove = -1
        labels = getattr(self.parent_resource_version, self.parent_list_attribute)
        for i, label in enumerate(labels):
            if label.uuid == obj.uuid:
                index_to_remove = i
                break
        if index_to_remove >= 0:
            del labels[index_to_remove]
            self.parent_resource_version.update_comment = 'Deleted %s from %s.' % (obj.name, self.parent_list_attribute)
            ConceptVersion.persist_clone(self.parent_resource_version)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConceptNameRetrieveUpdateDestroyView(ConceptLabelRetrieveUpdateDestroyView):
    parent_list_attribute = 'names'
    serializer_class = ConceptNameSerializer


class ConceptDescriptionRetrieveUpdateDestroyView(ConceptLabelRetrieveUpdateDestroyView):
    parent_list_attribute = 'descriptions'
    serializer_class = ConceptDescriptionSerializer


class ConceptReferenceBaseView(VersionedResourceChildMixin):
    lookup_field = 'concept'
    pk_field = 'mnemonic'
    model = ConceptReference
    child_list_attribute = 'concept_references'
    updated_since = None
    reference_only = False

    def initialize(self, request, path_info_segment, **kwargs):
        self.reference_only = request.QUERY_PARAMS.get('reference', False)
        super(ConceptReferenceBaseView, self).initialize(request, path_info_segment, **kwargs)


class ConceptReferenceListCreateView(ConceptReferenceBaseView, CreateAPIView, ListWithHeadersMixin):
    permission_classes = (CanEditParentDictionary,)
    serializer_class = ConceptReferenceCreateSerializer

    def get(self, request, *args, **kwargs):
        self.updated_since = parse_updated_since_param(request)
        self.permission_classes = (CanViewParentDictionary,)
        self.serializer_class = ConceptReferenceDetailSerializer if self.reference_only else ReferencesToVersionsSerializer
        return self.list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            save_kwargs = {
                'force_insert': True,
                'owner': request.user,
                'parent_resource': self.parent_resource,
                'child_list_attribute': self.child_list_attribute
            }
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                serializer = ConceptReferenceDetailSerializer(self.object)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = super(ConceptReferenceListCreateView, self).get_queryset()
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        return queryset


class ConceptReferenceRetrieveUpdateDestroyView(ConceptReferenceBaseView, RetrieveUpdateDestroyAPIView):
    permission_classes = (CanEditParentDictionary,)
    serializer_class = ConceptReferenceDetailSerializer

    def initialize(self, request, path_info_segment, **kwargs):
        self.reference_only = request.QUERY_PARAMS.get('reference', False)
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=2)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)

    def get(self, request, *args, **kwargs):
        self.permission_classes = (CanViewParentDictionary,)
        self.serializer_class = ConceptReferenceDetailSerializer if self.reference_only else ConceptVersionDetailSerializer
        return super(ConceptReferenceRetrieveUpdateDestroyView, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super(ConceptReferenceRetrieveUpdateDestroyView, self).get_object(queryset)
        return obj if self.reference_only else self.resolve_reference(obj)

    def resolve_reference(self, concept_reference):
        if concept_reference.concept_version:
            return concept_reference.concept_version
        elif concept_reference.source_version:
            concept_versions = ConceptVersion.objects.filter(id__in=concept_reference.source_version.concepts)
            return concept_versions.get(versioned_object_id=concept_reference.concept.id)
        return ConceptVersion.get_latest_version_of(concept_reference.concept)
