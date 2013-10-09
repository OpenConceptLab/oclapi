from django.db.models import Q
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from oclapi.permissions import HasOwnership
from oclapi.views import SubResourceMixin
from sources.models import Source, EDIT_ACCESS_TYPE, VIEW_ACCESS_TYPE
from sources.serializers import SourceCreateSerializer, SourceListSerializer, SourceDetailSerializer


class SourceBaseView(SubResourceMixin):
    lookup_field = 'source'
    pk_field = 'mnemonic'
    model = Source
    queryset = Source.objects.filter(is_active=True)
    base_or_clause = [Q(public_access=EDIT_ACCESS_TYPE), Q(public_access=VIEW_ACCESS_TYPE)]
    permission_classes = (HasOwnership,)


class SourceDetailView(SourceBaseView, RetrieveAPIView):
    serializer_class = SourceDetailSerializer


class SourceListView(SourceBaseView,
                     mixins.CreateModelMixin,
                     mixins.ListModelMixin):

    def get(self, request, *args, **kwargs):
        self.serializer_class = SourceListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = SourceCreateSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
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

