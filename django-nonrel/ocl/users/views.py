from rest_framework import generics, mixins, status
from rest_framework.response import Response
from orgs.models import Organization
from users.models import UserProfile
from users.serializers import UserListSerializer, UserCreateSerializer, UserUpdateSerializer, UserDetailSerializer


class UserListView(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   generics.GenericAPIView):
    queryset = UserProfile.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        self.serializer_class = UserListSerializer
        related_object_type = kwargs.pop('related_object_type', None)
        related_object_kwarg = kwargs.pop('related_object_kwarg', None)
        if related_object_type and related_object_kwarg:
            related_object_key = kwargs.pop(related_object_kwarg)
            if Organization == related_object_type:
                organization = Organization.objects.get(mnemonic=related_object_key)
                member_ids = organization.members
                self.queryset = UserProfile.objects.filter(mnemonic__in=member_ids)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = UserCreateSerializer
        return self.create(request, *args, **kwargs)


class UserDetailReadOnlyView(mixins.RetrieveModelMixin,
                             generics.GenericAPIView):
    queryset = UserProfile.objects.filter(is_active=True)
    serializer_class = UserDetailSerializer
    lookup_field = 'mnemonic'
    user_is_self = False

    def get(self, request, *args, **kwargs):
        self.user_is_self = kwargs.pop('user_is_self', False)
        return self.retrieve(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if self.user_is_self:
            return self.request.user.get_profile()
        return super(UserDetailReadOnlyView, self).get_object(queryset)


class UserDetailView(UserDetailReadOnlyView,
                     mixins.UpdateModelMixin):
    serializer_class = UserUpdateSerializer

    def put(self, request, *args, **kwargs):
        self.user_is_self = kwargs.pop('user_is_self', False)
        return self.partial_update(request, *args, **kwargs)


class UserRUDView(UserDetailView,
                  mixins.DestroyModelMixin):
    serializer_class = UserDetailSerializer

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
