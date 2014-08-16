from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, get_object_or_404, UpdateAPIView, DestroyAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView
from rest_framework.response import Response
from concepts.models import Concept, ConceptVersion, ConceptReference
from concepts.permissions import CanViewParentDictionary, CanEditParentDictionary
from concepts.serializers import ConceptCreateSerializer, ConceptDetailSerializer, ConceptVersionListSerializer, ConceptVersionDetailSerializer, ConceptVersionUpdateSerializer, ConceptReferenceCreateSerializer, ConceptReferenceDetailSerializer
from oclapi.views import ConceptDictionaryMixin, VersionedResourceChildMixin, BaseAPIView, ListWithHeadersMixin, ChildResourceMixin
from sources.models import SourceVersion


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

    def get(self, request, *args, **kwargs):
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        return self.list(request, *args, **kwargs)


class ConceptCreateView(ConceptBaseView,
                        mixins.CreateModelMixin):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            delegate_view = ConceptVersionListView.as_view()
            return delegate_view(request, *args, **kwargs)
        return super(ConceptCreateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = ConceptCreateSerializer
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
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ConceptVersion.objects.filter(versioned_object_id=self.parent_resource.id)


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

    def get(self, request, *args, **kwargs):
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        return self.list(request, *args, **kwargs)


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


class ConceptReferenceBaseView(VersionedResourceChildMixin):
    lookup_field = 'concept'
    pk_field = 'mnemonic'
    model = ConceptReference
    child_list_attribute = 'concept_references'


class ConceptReferenceListCreateView(ConceptReferenceBaseView, CreateAPIView, ListWithHeadersMixin):
    permission_classes = (CanEditParentDictionary,)
    serializer_class = ConceptReferenceCreateSerializer

    def get(self, request, *args, **kwargs):
        self.permission_classes = (CanViewParentDictionary,)
        self.serializer_class = ConceptReferenceDetailSerializer
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


class ConceptReferenceRetrieveUpdateDestroyView(ConceptReferenceBaseView, RetrieveUpdateDestroyAPIView):
    permission_classes = (CanEditParentDictionary,)
    serializer_class = ConceptReferenceDetailSerializer
    reference_only = False

    def initialize(self, request, path_info_segment, **kwargs):
        self.reference_only = request.QUERY_PARAMS.get('reference', False)
        super(ConceptReferenceRetrieveUpdateDestroyView, self).initialize(request, path_info_segment, **kwargs)

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
