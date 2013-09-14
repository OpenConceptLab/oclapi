from django.contrib.auth.models import Group
from rest_framework import generics, mixins, viewsets, status
from rest_framework.response import Response
from accounts.models import UserProfile
from accounts.serializers import UserListSerializer, UserCreateSerializer, UserUpdateSerializer, UserDetailSerializer, GroupSerializer


class UserListView(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   generics.GenericAPIView):
    queryset = UserProfile.objects.select_related().filter(user__is_active=True)

    def get(self, request, *args, **kwargs):
        self.serializer_class = UserListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = UserCreateSerializer
        return self.create(request, *args, **kwargs)


class UserDetailReadOnlyView(mixins.RetrieveModelMixin,
                             generics.GenericAPIView):
    queryset = UserProfile.objects.select_related().filter(user__is_active=True)
    serializer_class = UserDetailSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class UserDestroyView(UserDetailReadOnlyView,
                      mixins.DestroyModelMixin):

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.user.is_active = False
        obj.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDetailView(UserDetailReadOnlyView,
                     mixins.UpdateModelMixin):

    def put(self, request, *args, **kwargs):
        self.serializer_class = UserUpdateSerializer
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.get_profile()


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer