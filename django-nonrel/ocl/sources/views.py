from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from oclapi.permissions import HasPrivateAccess
from oclapi.views import SubResourceMixin
from sources.models import Source, EDIT_ACCESS_TYPE, VIEW_ACCESS_TYPE
from sources.permissions import CanViewSource, CanEditSource
from sources.serializers import SourceCreateSerializer, SourceListSerializer, SourceDetailSerializer, SourceUpdateSerializer


class SourceBaseView(SubResourceMixin):
    lookup_field = 'source'
    pk_field = 'mnemonic'
    model = Source
    queryset = Source.objects.filter(is_active=True)
    base_or_clause = [Q(public_access=EDIT_ACCESS_TYPE), Q(public_access=VIEW_ACCESS_TYPE)]
    permission_classes = (HasPrivateAccess,)


class SourceUpdateDetailView(SourceBaseView, RetrieveAPIView, UpdateAPIView):

    def initial(self, request, *args, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewSource,)
            self.serializer_class = SourceDetailSerializer
        else:
            self.permission_classes = (CanEditSource,)
            self.serializer_class = SourceUpdateSerializer
        super(SourceUpdateDetailView, self).initial(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        self.object = self.get_object()
        created = False
        save_kwargs = {'force_update': True, 'parent_resource': self.parent_resource}
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

