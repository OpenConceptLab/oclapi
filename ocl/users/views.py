from datetime import timedelta

from django.conf import settings
from django.core.signing import BadSignature
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.http import urlencode
from rest_framework import mixins, status, views
from rest_framework.authtoken.models import Token
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin
from oclapi.utils import timestamp_unsign
from oclapi.views import BaseAPIView
from orgs.models import Organization
from tasks import send_verify_email_message
from users.constants import SUCCESS_URL_PARAM, FAILURE_URL_PARAM, VERIFY_EMAIL_MESSAGE
from users.models import UserProfile
from users.serializers import UserListSerializer, UserCreateSerializer, UserDetailSerializer, RedirectParamsSerializer, \
    LoginSerializer
from django.contrib.auth.hashers import check_password


OCL_WEB_BASE_URL = settings.BASE_URL.replace("api.", "")


def build_redirect_urls(data):
    return urlencode({
        SUCCESS_URL_PARAM: data.get('email_verify_success_url', OCL_WEB_BASE_URL),
        FAILURE_URL_PARAM: data.get('email_verify_failure_url', OCL_WEB_BASE_URL),
    })


class BaseSignUpView(BaseAPIView, mixins.CreateModelMixin):
    model = UserProfile
    verified_email = True

    def initial(self, request, *args, **kwargs):
        self.related_object_type = kwargs.pop('related_object_type', None)
        self.related_object_kwarg = kwargs.pop('related_object_kwarg', None)
        super(BaseSignUpView, self).initial(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.related_object_type and self.related_object_kwarg:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.serializer_class = UserCreateSerializer
        return self.create(request, *args, **kwargs)

    def pre_save(self, obj):
        obj.verified_email = self.verified_email
        super(BaseSignUpView, self).pre_save(obj)


class UserSignUpView(BaseSignUpView):
    """ general, non admin privileged signup """

    permission_classes = (AllowAny,)
    verified_email = False

    def post(self, request, *args, **kwargs):
        redirect_params_serializer = RedirectParamsSerializer(data=request.DATA)
        if not redirect_params_serializer.is_valid():
            return Response(redirect_params_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        signup_response = super(UserSignUpView, self).post(request, *args, **kwargs)
        if signup_response.status_code == status.HTTP_201_CREATED:
            profile = UserProfile.objects.get(mnemonic=signup_response.data['username'])
            send_verify_email_message.delay(
                profile.name,
                profile.email,
                profile.get_verify_email_url(request),
                build_redirect_urls(redirect_params_serializer.data),
            )
        return signup_response

    def get(self, request, verification_token):
        try:
            username = timestamp_unsign(verification_token, timedelta(days=2))
        except BadSignature:
            return redirect(request.QUERY_PARAMS.get(FAILURE_URL_PARAM, OCL_WEB_BASE_URL))

        profile = UserProfile.objects.get(mnemonic=username)
        profile.verified_email = True
        profile.save()

        return redirect(request.QUERY_PARAMS.get(SUCCESS_URL_PARAM, OCL_WEB_BASE_URL))


class UserListView(BaseSignUpView,
                   ListWithHeadersMixin):
    queryset = UserProfile.objects.filter(is_active=True)
    filter_backends = [HaystackSearchFilter]
    solr_fields = {
        'username': {'sortable': True, 'filterable': False},
        'dateJoined': {'sortable': True, 'default': 'asc', 'filterable': False},
        'company': {'sortable': False, 'filterable': True},
        'location': {'sortable': False, 'filterable': True},
    }

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            self.permission_classes = (IsAdminUser, )
        super(UserListView, self).initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.serializer_class = UserDetailSerializer if self.is_verbose(request) else UserListSerializer
        if self.related_object_type and self.related_object_kwarg:
            related_object_key = kwargs.pop(self.related_object_kwarg)
            if Organization == self.related_object_type:
                organization = Organization.objects.get(mnemonic=related_object_key)
                if organization.public_access == 'None':
                    if not request.user.is_staff:
                        if request.user.get_profile().id not in organization.members:
                            return HttpResponse(status=status.HTTP_403_FORBIDDEN)
                self.queryset = UserProfile.objects.filter(id__in=organization.members)
        return self.list(request, *args, **kwargs)


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
        password = request.DATA.get('password')
        hashed_password = request.DATA.get('hashed_password')
        if password:
            obj = self.get_object()
            obj.user.set_password(password)
            obj.save()
            Token.objects.filter(user=obj.user).delete()
            Token.objects.create(user=obj.user)
        elif hashed_password:
            obj = self.get_object()
            obj.hashed_password = hashed_password
            obj.save()
            Token.objects.filter(user=obj.user).delete()
            Token.objects.create(user=obj.user)

        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if self.user_is_self:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        obj = self.get_object()
        obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserLoginView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.data.get('username')
        password = serializer.data.get('password', None)
        hashed_password = serializer.data.get('hashed_password', None)

        try:
            profile = UserProfile.objects.get(mnemonic=username)
            if check_password(password, profile.hashed_password) or hashed_password == profile.hashed_password:
                if profile.verified_email:
                    return Response({'token': profile.user.auth_token.key}, status=status.HTTP_200_OK)
                send_verify_email_message.delay(
                    profile.name,
                    profile.email,
                    profile.get_verify_email_url(request),
                    build_redirect_urls(serializer.data),
                )
                return Response({'detail': VERIFY_EMAIL_MESSAGE}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'detail': 'No such user or wrong password.'}, status=status.HTTP_401_UNAUTHORIZED)

        except UserProfile.DoesNotExist:
            return Response({'detail': 'No such user or wrong password.'}, status=status.HTTP_401_UNAUTHORIZED)


class UserReactivateView(UserBaseView, UpdateAPIView):
    permission_classes = (IsAdminUser, )
    queryset = UserProfile.objects.filter(is_active=False)

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        profile.undelete()
        return Response(status=status.HTTP_204_NO_CONTENT)

