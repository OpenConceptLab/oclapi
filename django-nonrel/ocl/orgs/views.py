from django.http import HttpResponse
from rest_framework import generics, mixins, status
from rest_framework.compat import View
from rest_framework.response import Response
from orgs.models import Organization
from orgs.serializers import OrganizationListSerializer, OrganizationCreateSerializer, OrganizationDetailSerializer, OrganizationUpdateSerializer
from users.models import UserProfile


class OrganizationListView(mixins.CreateModelMixin,
                           mixins.ListModelMixin,
                           generics.GenericAPIView):
    queryset = Organization.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        user_is_self = kwargs.pop('user_is_self', False)
        if user_is_self:
            user_groups = request.user.groups.all()
            self.queryset = Organization.objects.filter(group__in=user_groups)
        self.serializer_class = OrganizationListSerializer
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = OrganizationCreateSerializer
        return self.create(request, *args, **kwargs)


class OrganizationDetailView(mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.DestroyModelMixin,
                             generics.GenericAPIView):
    serializer_class = OrganizationDetailSerializer
    queryset = Organization.objects.filter(is_active=True)
    lookup_field = 'mnemonic'

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
        self._get_group_and_user(request, *args, **kwargs)
        if self.userprofile.mnemonic in self.organization.members:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        self._get_group_and_user(request, *args, **kwargs)
        if not self.userprofile.mnemonic in self.organization.members:
            self.organization.group.user_set.add(self.userprofile.user)
            self.organization.members.append(self.userprofile.mnemonic)
            self.organization.save()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        self._get_group_and_user(request, *args, **kwargs)
        if self.userprofile.mnemonic in self.organization.members:
            self.organization.group.user_set.remove(self.userprofile.user)
            self.organization.members.remove(self.userprofile.mnemonic)
            self.organization.save()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def _get_group_and_user(self, request, *args, **kwargs):
        org_id = kwargs.pop('mnemonic')
        self.organization = Organization.objects.get(mnemonic=org_id)
        userprofile_id = kwargs.pop('uid')
        self.userprofile = UserProfile.objects.get(mnemonic=userprofile_id)
