from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from oclapi.filters import HaystackSearchFilter
from oclapi.views import BaseAPIView, ListWithHeadersMixin
from orgs.models import Organization
from users.models import UserProfile
from users.serializers import UserListSerializer, UserCreateSerializer, UserUpdateSerializer, UserDetailSerializer


class UserListView(BaseAPIView,
                   ListWithHeadersMixin,
                   mixins.CreateModelMixin):
    model = UserProfile
    queryset = UserProfile.objects.filter(is_active=True)
    filter_backends = [HaystackSearchFilter]
    solr_fields = {
        'username': {'sortable': True, 'filterable': False}
    }
    verbose = False

    def initial(self, request, *args, **kwargs):
        self.verbose = request.QUERY_PARAMS.get('verbose', False)
        self.related_object_type = kwargs.pop('related_object_type', None)
        self.related_object_kwarg = kwargs.pop('related_object_kwarg', None)
        if request.method == 'POST':
            self.permission_classes = (IsAdminUser, )
        super(UserListView, self).initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.serializer_class = UserDetailSerializer if self.verbose else UserListSerializer
        if self.related_object_type and self.related_object_kwarg:
            related_object_key = kwargs.pop(self.related_object_kwarg)
            if Organization == self.related_object_type:
                organization = Organization.objects.get(mnemonic=related_object_key)
                if request.user.get_profile().id not in organization.members and not request.user.is_staff:
                    return HttpResponse(status=status.HTTP_403_FORBIDDEN)
                self.queryset = UserProfile.objects.filter(id__in=organization.members)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.related_object_type and self.related_object_kwarg:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.serializer_class = UserCreateSerializer
        return self.create(request, *args, **kwargs)


class UserBaseView(BaseAPIView):
    lookup_field = 'user'
    model = UserProfile
    queryset = UserProfile.objects.filter(is_active=True)
    user_is_self = False

    def initialize(self, request, path_info_segment, **kwargs):
        super(UserBaseView, self).initialize(request, path_info_segment, **kwargs)
        if (request.method == 'DELETE') or (request.method == 'POST' and not self.user_is_self):
            self.permission_classes = (IsAdminUser, )


class UserDetailView(UserBaseView,
                     RetrieveAPIView,
                     mixins.UpdateModelMixin):
    serializer_class = UserDetailSerializer

    def get_object(self, queryset=None):
        if self.user_is_self:
            return self.request.user.get_profile()
        return super(UserDetailView, self).get_object(queryset)

    def post(self, request, *args, **kwargs):
        self.serializer_class = UserUpdateSerializer
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if self.user_is_self:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        obj = self.get_object()
        obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
