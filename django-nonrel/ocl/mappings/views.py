# Create your views here.
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.response import Response
from mappings.models import Mapping
from mappings.serializers import MappingSerializer
from oclapi.filters import HaystackSearchFilter
from oclapi.permissions import HasOwnership
from oclapi.views import SubResourceMixin, ListWithHeadersMixin


class MappingBaseView(SubResourceMixin):
    lookup_field = 'mapping'
    pk_field = 'id'
    model = Mapping
    permission_classes = (HasOwnership,)
    child_list_attribute = 'mappings'


class MappingListView(MappingBaseView,
                      ListAPIView,
                      CreateAPIView,
                      ListWithHeadersMixin,
                      mixins.CreateModelMixin):
    serializer_class = MappingSerializer
    filter_backends = [HaystackSearchFilter]
    solr_fields = {
        'map_type': {'sortable': True, 'filterable': True}
    }

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
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MappingDetailView(MappingBaseView, RetrieveAPIView):
    serializer_class = MappingSerializer




