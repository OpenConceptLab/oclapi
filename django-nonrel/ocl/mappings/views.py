from itertools import chain
from django.core.exceptions import ValidationError
from django.db.models.query import EmptyQuerySet
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.response import Response
from mappings.filters import MappingSearchFilter
from mappings.models import Mapping
from mappings.permissions import CanEditParentSource, CanViewParentSource
from mappings.serializers import MappingCreateSerializer, MappingRetrieveDestroySerializer, MappingUpdateSerializer
from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin
from oclapi.views import ChildResourceMixin


class MappingBaseView(ChildResourceMixin):
    lookup_field = 'mapping'
    pk_field = 'id'
    model = Mapping
    queryset = Mapping.objects.filter(is_active=True)
    permission_classes = (CanEditParentSource,)
    child_list_attribute = 'mappings'

    def initialize(self, request, path_info_segment, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewParentSource,)
        super(MappingBaseView, self).initialize(request, path_info_segment, **kwargs)


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
        include_inverse_param = request.GET.get('includeInverseMappings', '0')
        self.include_inverse_mappings = '1' == include_inverse_param
        self.serializer_class = MappingRetrieveDestroySerializer
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
            self.object = serializer.save(force_insert=True, owner=request.user, parent_resource=self.parent_resource)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                serializer = MappingRetrieveDestroySerializer(self.object)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_inverse_queryset(self):
        if not self.parent_resource:
            return EmptyQuerySet()
        queryset = super(ChildResourceMixin, self).get_queryset()
        queryset = queryset.filter(to_concept=self.parent_resource)
        return queryset


class MappingDetailView(MappingBaseView, RetrieveAPIView, UpdateAPIView, DestroyAPIView):
    serializer_class = MappingRetrieveDestroySerializer

    def update(self, request, *args, **kwargs):
        self.serializer_class = MappingUpdateSerializer
        partial = True
        self.object = self.get_object_or_none()

        if self.object is None:
            created = True
            save_kwargs = {'force_insert': True}
            success_status_code = status.HTTP_201_CREATED
        else:
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
            serializer = MappingRetrieveDestroySerializer(self.object)
            return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



