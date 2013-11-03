from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, get_object_or_404, ListAPIView, DestroyAPIView
from rest_framework.response import Response
from conceptcollections.serializers import CollectionDetailSerializer, CollectionUpdateSerializer, CollectionListSerializer, CollectionCreateSerializer, CollectionVersionListSerializer, CollectionVersionCreateSerializer, CollectionVersionDetailSerializer, CollectionVersionUpdateSerializer
from oclapi.permissions import HasPrivateAccess, HasAccessToVersionedObject
from oclapi.views import SubResourceMixin, ResourceVersionMixin, ResourceAttributeChildMixin
from conceptcollections.models import VIEW_ACCESS_TYPE, EDIT_ACCESS_TYPE, Collection, CollectionVersion
from conceptcollections.permissions import CanViewCollection, CanEditCollection


class CollectionBaseView(SubResourceMixin):
    lookup_field = 'collection'
    pk_field = 'mnemonic'
    model = Collection
    queryset = Collection.objects.filter(is_active=True)
    base_or_clause = [Q(public_access=EDIT_ACCESS_TYPE), Q(public_access=VIEW_ACCESS_TYPE)]
    permission_classes = (HasPrivateAccess,)


class CollectionRetrieveUpdateDestroyView(CollectionBaseView, RetrieveAPIView, UpdateAPIView, DestroyAPIView):

    def initial(self, request, *args, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewCollection,)
            self.serializer_class = CollectionDetailSerializer
        else:
            self.permission_classes = (CanEditCollection,)
            self.serializer_class = CollectionUpdateSerializer
        super(CollectionRetrieveUpdateDestroyView, self).initial(request, *args, **kwargs)

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


class CollectionListView(CollectionBaseView,
                         mixins.CreateModelMixin,
                         mixins.ListModelMixin):

    def get(self, request, *args, **kwargs):
        self.serializer_class = CollectionListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = CollectionCreateSerializer
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


class CollectionVersionBaseView(ResourceVersionMixin):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    queryset = CollectionVersion.objects.filter(is_active=True)
    permission_classes = (HasAccessToVersionedObject,)


class CollectionVersionListView(CollectionVersionBaseView,
                                mixins.CreateModelMixin,
                                mixins.ListModelMixin):

    def get(self, request, *args, **kwargs):
        self.serializer_class = CollectionVersionListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = CollectionVersionCreateSerializer
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


class CollectionVersionRetrieveUpdateView(CollectionVersionBaseView, RetrieveAPIView, UpdateAPIView):
    is_latest = False

    def initial(self, request, *args, **kwargs):
        if 'GET' == request.method:
            self.permission_classes = (CanViewCollection,)
            self.serializer_class = CollectionVersionDetailSerializer
        else:
            self.permission_classes = (CanEditCollection,)
            self.serializer_class = CollectionVersionUpdateSerializer
        super(CollectionVersionRetrieveUpdateView, self).initial(request, *args, **kwargs)

    def initialize(self, request, path_info_segment, **kwargs):
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


class CollectionVersionChildListView(ResourceAttributeChildMixin, ListAPIView):
    lookup_field = 'version'
    pk_field = 'mnemonic'
    model = CollectionVersion
    permission_classes = (HasAccessToVersionedObject,)
    serializer_class = CollectionVersionListSerializer

    def get_queryset(self):
        queryset = super(CollectionVersionChildListView, self).get_queryset()
        return queryset.filter(parent_version=self.resource_version)
