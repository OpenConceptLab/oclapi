from django.http import HttpResponse
from rest_framework import generics, mixins, status
from rest_framework.compat import View
from rest_framework.response import Response
from accounts.models import UserProfile, Organization
from accounts.serializers import UserListSerializer, UserCreateSerializer, UserUpdateSerializer, UserDetailSerializer, OrganizationListSerializer, OrganizationCreateSerializer, OrganizationDetailSerializer, OrganizationUpdateSerializer


class UserListView(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   generics.GenericAPIView):
    queryset = UserProfile.objects.select_related().filter(user__is_active=True)

    def get(self, request, *args, **kwargs):
        self.serializer_class = UserListSerializer
        related_object_type = kwargs.pop('related_object_type', None)
        related_object_id = kwargs.pop('pk', None)
        if related_object_type and related_object_id:
            if Organization == related_object_type:
                organization = Organization.objects.get(id=related_object_id)
                users = organization.group.user_set.all()
                self.queryset = self.queryset.filter(user__in=users)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = UserCreateSerializer
        return self.create(request, *args, **kwargs)


class UserDetailReadOnlyView(mixins.RetrieveModelMixin,
                             generics.GenericAPIView):
    queryset = UserProfile.objects.select_related().filter(user__is_active=True)
    serializer_class = UserDetailSerializer
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

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.user.is_active = False
        obj.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationListView(mixins.ListModelMixin,
                           generics.GenericAPIView):
    queryset = Organization.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        user_is_self = kwargs.pop('user_is_self', False)
        if user_is_self:
            user_groups = request.user.groups.all()
            self.queryset = Organization.objects.filter(group__in=user_groups)
        self.serializer_class = OrganizationListSerializer
        return self.list(request, *args, **kwargs)


class OrganizationCreateView(mixins.CreateModelMixin,
                             generics.GenericAPIView):

    def post(self, request, *args, **kwargs):
        self.serializer_class = OrganizationCreateSerializer
        return self.create(request, *args, **kwargs)


class OrganizationDetailView(mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.DestroyModelMixin,
                             generics.GenericAPIView):
    serializer_class = OrganizationDetailSerializer
    queryset = Organization.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = OrganizationUpdateSerializer
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationMemberView(View):

    def get(self, request, *args, **kwargs):
        group, user = self._get_group_and_user(request, *args, **kwargs)
        if user in group.user_set.all():
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        group, user = self._get_group_and_user(request, *args, **kwargs)
        if user not in group.user_set.all():
            group.user_set.add(user)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        group, user = self._get_group_and_user(request, *args, **kwargs)
        if user in group.user_set.all():
            group.user_set.remove(user)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def _get_group_and_user(self, request, *args, **kwargs):
        org_pk = kwargs.pop('pk')
        org = Organization.objects.get(id=org_pk)
        group = org.group

        userprofile_id = kwargs.pop('uid')
        userprofile = UserProfile.objects.get(id=userprofile_id)
        user = userprofile.user

        return group, user



