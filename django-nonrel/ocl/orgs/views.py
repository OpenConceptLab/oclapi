from django.http import HttpResponse
from rest_framework import mixins, status, generics
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from oclapi.permissions import IsOrganizationMember
from oclapi.views import BaseAPIView
from orgs.models import Organization
from orgs.serializers import OrganizationListSerializer, OrganizationCreateSerializer, OrganizationDetailSerializer, OrganizationUpdateSerializer
from users.models import UserProfile


def add_user_to_org(userprofile, organization):
    if not userprofile.mnemonic in organization.members:
            rollback = True
            exception = None
            try:
                organization.group.user_set.add(userprofile.user)
                organization.members.append(userprofile.mnemonic)
                userprofile.organizations.append(organization.mnemonic)
                organization.save()
                userprofile.save()
                rollback = False
            except Exception as e:
                exception = e
            finally:
                if rollback:
                    try:
                        userprofile.organizations.remove(organization.mnemonic)
                    except: pass
                    try:
                        organization.members.remove(userprofile.mnemonic)
                    except: pass
                    try:
                        organization.group.user_set.remove(userprofile.user)
                    except: pass
                    try:
                        organization.save()
                    except: pass
                    try:
                        userprofile.save()
                    except: pass
                    raise exception
                return True


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
            self.queryset = self.queryset.filter(mnemonic__in=restrict_to)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.related_object_type or self.related_object_kwarg:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.serializer_class = OrganizationCreateSerializer
        response = self.create(request, *args, **kwargs)
        if response.status_code == 201:
            try:
                add_user_to_org(request.user.get_profile(), self.object)
                return response
            except Exception as e:
                self.object.delete()
                raise e
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
            self.permission_classes = (IsOrganizationMember, )
        super(OrganizationDetailView, self).initial(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = OrganizationUpdateSerializer
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationMemberView(generics.GenericAPIView):

    def initial(self, request, *args, **kwargs):
        org_id = kwargs.pop('org')
        self.organization = Organization.objects.get(mnemonic=org_id)
        userprofile_id = kwargs.pop('user')
        self.userprofile = UserProfile.objects.get(mnemonic=userprofile_id)
        super(OrganizationMemberView, self).initial(request, *args, **kwargs)
        self.user_in_org = request.user.is_authenticated and request.user.get_profile().mnemonic in self.organization.members

    def get(self, request, *args, **kwargs):
        self.initial(request, *args, **kwargs)
        if not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        if self.userprofile.mnemonic in self.organization.members:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        if not request.user.is_staff or not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        add_user_to_org(self.userprofile, self.organization)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff or not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        if self.userprofile.mnemonic in self.organization.members:
            rollback = True
            exception = None
            try:
                self.organization.group.user_set.remove(self.userprofile.user)
                self.organization.members.remove(self.userprofile.mnemonic)
                self.userprofile.organizations.remove(self.organization.mnemonic)
                self.organization.save()
                self.userprofile.save()
                rollback = False
            except Exception as e:
                exception = e
            finally:
                if rollback:
                    try:
                        self.userprofile.organizations.append(self.organization.mnemonic)
                    except: pass
                    try:
                        self.organization.members.append(self.userprofile.mnemonic)
                    except: pass
                    try:
                        self.organization.group.user_set.add(self.userprofile.user)
                    except: pass
                    try:
                        self.organization.save()
                    except: pass
                    try:
                        self.userprofile.save()
                    except: pass
                    raise exception
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
