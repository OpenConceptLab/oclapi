from django.http import HttpResponse
from rest_framework import mixins, status, generics
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from oclapi.permissions import HasOwnership
from oclapi.utils import add_user_to_org, remove_user_from_org
from oclapi.views import BaseAPIView
from orgs.models import Organization
from orgs.serializers import OrganizationListSerializer, OrganizationCreateSerializer, OrganizationDetailSerializer, OrganizationUpdateSerializer
from users.models import UserProfile


class OrganizationListView(mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           generics.GenericAPIView):
    queryset = Organization.objects.filter(is_active=True)

    def initial(self, request, *args, **kwargs):
        self.user_is_self = kwargs.pop('user_is_self', False)
        self.related_object_type = kwargs.pop('related_object_type', None)
        self.related_object_kwarg = kwargs.pop('related_object_kwarg', None)
        super(OrganizationListView, self).initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.serializer_class = OrganizationListSerializer
        restrict_to = None
        if self.user_is_self:
            restrict_to = request.user.get_profile().organizations
        else:
            if self.related_object_type and self.related_object_kwarg:
                related_object_key = kwargs.pop(self.related_object_kwarg)
                if UserProfile == self.related_object_type:
                    userprofile = UserProfile.objects.get(mnemonic=related_object_key)
                    restrict_to = userprofile.organizations
        if restrict_to is not None:
            self.queryset = self.queryset.filter(id__in=restrict_to)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.related_object_type or self.related_object_kwarg:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.serializer_class = OrganizationCreateSerializer
        response = self.create(request, *args, **kwargs)
        if response.status_code == 201:
            add_user_to_org(request.user.get_profile(), self.object)
        return response


class OrganizationBaseView(BaseAPIView, RetrieveAPIView):
    lookup_field = 'org'
    model = Organization
    queryset = Organization.objects.filter(is_active=True)


class OrganizationDetailView(mixins.UpdateModelMixin,
                             OrganizationBaseView):
    serializer_class = OrganizationDetailSerializer
    queryset = Organization.objects.filter(is_active=True)

    def initial(self, request, *args, **kwargs):
        if (request.method == 'DELETE') or (request.method == 'POST'):
            self.permission_classes = (HasOwnership, )
        super(OrganizationDetailView, self).initial(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = OrganizationUpdateSerializer
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationMemberView(generics.GenericAPIView):

    def initial(self, request, *args, **kwargs):
        org_id = kwargs.pop('org')
        self.organization = Organization.objects.get(mnemonic=org_id)
        userprofile_id = kwargs.pop('user')
        self.userprofile = UserProfile.objects.get(mnemonic=userprofile_id)
        super(OrganizationMemberView, self).initial(request, *args, **kwargs)
        self.user_in_org = request.user.is_authenticated and request.user.get_profile().id in self.organization.members

    def get(self, request, *args, **kwargs):
        self.initial(request, *args, **kwargs)
        if not self.user_in_org and not request.user.is_staff:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        if self.userprofile.id in self.organization.members:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        if not request.user.is_staff and not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        add_user_to_org(self.userprofile, self.organization)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff and not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        remove_user_from_org(self.userprofile, self.organization)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
