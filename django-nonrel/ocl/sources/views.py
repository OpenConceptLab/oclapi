from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from oclapi.permissions import HasOwnership
from oclapi.views import SubResourceMixin
from sources.models import Source
from sources.serializers import SourceCreateSerializer, SourceListSerializer, SourceDetailSerializer


class SourceBaseView(SubResourceMixin):
    lookup_field = 'mnemonic'
    model = Source
    queryset = Source.objects.filter(is_active=True)
    url_param = 'source'
    permission_classes = (HasOwnership,)


class SourceDetailView(RetrieveAPIView,
                       SourceBaseView):
    serializer_class = SourceDetailSerializer


class SourceListView(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     SourceBaseView):

    def get(self, request, *args, **kwargs):
        self.serializer_class = SourceListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = SourceCreateSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        parent_resource = self.get_parent_resource()
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, owner=request.user, parent_resource=parent_resource)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

