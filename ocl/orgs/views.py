from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status, generics
from rest_framework.generics import RetrieveAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from concepts.permissions import CanViewParentDictionary
from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin
from oclapi.models import ACCESS_TYPE_NONE
from oclapi.permissions import HasOwnership, IsSuperuser, CanViewConceptDictionary, CanEditConceptDictionary
from oclapi.utils import add_user_to_org, remove_user_from_org
from oclapi.views import BaseAPIView
from orgs.models import Organization
from orgs.serializers import OrganizationListSerializer, OrganizationCreateSerializer, OrganizationDetailSerializer
from users.models import UserProfile


class OrganizationListView(BaseAPIView,
                           ListWithHeadersMixin,
                           mixins.CreateModelMixin):
    model = Organization
    queryset = Organization.objects.filter(is_active=True)
    permission_classes = (CanViewConceptDictionary,)
    filter_backends = [HaystackSearchFilter]
    solr_fields = {
        'name': {'sortable': True, 'filterable': False},
        'last_update': {'sortable': True, 'default': 'desc', 'filterable': False},
        'company': {'sortable': False, 'filterable': True},
        'location': {'sortable': False, 'filterable': True},
    }

    def initial(self, request, *args, **kwargs):
        if (request.method == 'POST'):
            self.permission_classes = (IsAuthenticated, )
        self.related_object_type = kwargs.pop('related_object_type', None)
        self.related_object_kwarg = kwargs.pop('related_object_kwarg', None)
        super(OrganizationListView, self).initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.serializer_class = OrganizationDetailSerializer if self.is_verbose(request) else OrganizationListSerializer
        if request.user.is_staff: #/orgs
            return self.list(request, *args, **kwargs)

        if self.related_object_type and self.related_object_kwarg: #/users/(user)/orgs/
            org_ids = []
            related_object_key = kwargs.pop(self.related_object_kwarg)
            if UserProfile == self.related_object_type:
                userprofile = UserProfile.objects.get(mnemonic=related_object_key)
                org_ids = userprofile.organizations
            self.queryset = self.queryset.filter(id__in=org_ids)
        elif self.user_is_self: #/user/orgs/
            self.queryset = self.queryset.filter(id__in=request.user.get_profile().organizations)
        else: #/orgs
            if isinstance(request.user, AnonymousUser):
                self.queryset = self.queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
            else:
                org_ids = request.user.get_profile().organizations
                self.queryset = self.queryset.filter(~Q(public_access=ACCESS_TYPE_NONE) | Q(id__in=org_ids))

        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.related_object_type or self.related_object_kwarg:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.serializer_class = OrganizationCreateSerializer
        response = self.create(request, *args, **kwargs)
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            add_user_to_org(request.user.get_profile(), self.object)
            headers = self.get_success_headers(serializer.data)
            serializer = OrganizationDetailSerializer(self.object, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationBaseView(BaseAPIView, RetrieveAPIView, DestroyAPIView):
    lookup_field = 'org'
    model = Organization
    permission_classes = (CanViewConceptDictionary,)
    queryset = Organization.objects.filter(is_active=True)


class OrganizationDetailView(mixins.UpdateModelMixin,
                             OrganizationBaseView):
    serializer_class = OrganizationDetailSerializer
    permission_classes = (CanViewConceptDictionary,)
    queryset = Organization.objects.filter(is_active=True)

    def initial(self, request, *args, **kwargs):
        if (request.method == 'DELETE'):
            self.permission_classes = (IsSuperuser, )
        if (request.method == 'POST'):
            self.permission_classes = (CanEditConceptDictionary, )
        super(OrganizationDetailView, self).initial(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            obj.delete()
        except Exception as ex:
            return Response({'detail': ex.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Successfully deleted org.'}, status=status.HTTP_200_OK)


class OrganizationMemberView(generics.GenericAPIView):
    userprofile = None
    user_in_org = False

    def initial(self, request, *args, **kwargs):
        org_id = kwargs.pop('org')
        self.organization = Organization.objects.get(mnemonic=org_id)
        userprofile_id = kwargs.pop('user')
        try:
            self.userprofile = UserProfile.objects.get(mnemonic=userprofile_id)
        except UserProfile.DoesNotExist: pass
        try:
            self.user_in_org = request.user.is_staff or (request.user.is_authenticated and request.user.get_profile().id in self.organization.members)
        except UserProfile.DoesNotExist: pass
        super(OrganizationMemberView, self).initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.initial(request, *args, **kwargs)
        if not self.user_in_org and not request.user.is_staff:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        if request.user.is_staff or (self.userprofile and self.userprofile.id in self.organization.members):
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        if not request.user.is_staff and not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        if not self.userprofile:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        add_user_to_org(self.userprofile, self.organization)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff and not self.user_in_org:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
        remove_user_from_org(self.userprofile, self.organization)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
