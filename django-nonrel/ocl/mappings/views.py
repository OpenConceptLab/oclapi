from itertools import chain
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.query import EmptyQuerySet
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response
from concepts.permissions import CanEditParentDictionary, CanViewParentDictionary
from mappings.filters import MappingSearchFilter
from mappings.models import Mapping
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer, MappingDetailSerializer, MappingListSerializer
from oclapi.mixins import ListWithHeadersMixin
from oclapi.models import ACCESS_TYPE_NONE
from oclapi.views import ConceptDictionaryMixin
from sources.models import SourceVersion

INCLUDE_RETIRED_PARAM = 'include_retired'


class MappingBaseView(ConceptDictionaryMixin):
    lookup_field = 'mapping'
    pk_field = 'id'
    model = Mapping
    child_list_attribute = 'mappings'
    include_retired = False
    permission_classes = (CanEditParentDictionary,)
    parent_resource_version = None
    parent_resource_version_model = SourceVersion
    child_list_attribute = 'mappings'

    def initialize(self, request, path_info_segment, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewParentDictionary,)
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


class MappingListView(MappingBaseView,
                      ListAPIView,
                      CreateAPIView,
                      ListWithHeadersMixin,
                      mixins.CreateModelMixin):
    serializer_class = MappingCreateSerializer
    solr_fields = {}
    filter_backends = [MappingSearchFilter]
    include_inverse_mappings = False

    def get(self, request, *args, **kwargs):
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        include_inverse_param = request.GET.get('include_inverse_mappings', 'false')
        self.include_inverse_mappings = 'true' == include_inverse_param
        self.serializer_class = MappingListSerializer
        return super(MappingListView, self).get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())
        if self.include_inverse_mappings:
            self.object_list = list(chain(self.object_list, self.filter_queryset(self.get_inverse_queryset())))

        # Switch between paginated or standard style responses
        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list, many=True)

        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
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
        all_children = getattr(self.parent_resource_version, self.child_list_attribute) or []
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        queryset = queryset.filter(id__in=all_children)
        return queryset

    def get_inverse_queryset(self):
        if not self.parent_resource:
            return EmptyQuerySet()
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        queryset = queryset.filter(to_concept=self.parent_resource)
        return queryset


class MappingDetailView(MappingBaseView, RetrieveAPIView, UpdateAPIView, DestroyAPIView):
    serializer_class = MappingDetailSerializer

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        Mapping.retire(obj, self.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
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



