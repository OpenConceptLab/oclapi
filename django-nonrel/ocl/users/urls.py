from django.conf.urls import patterns, url, include
from orgs.views import OrganizationListView
from users.models import UserProfile
from users.views import UserListView, UserDetailView, UserReactivateView, UserLoginView
from oclapi.models import NAMESPACE_PATTERN, CONCEPT_ID_PATTERN

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', UserListView.as_view(), name='userprofile-list'),
    url(r'^login/$', UserLoginView.as_view(), name='user-login'),
    url(r'^(?P<user>' + NAMESPACE_PATTERN + ')/$', UserDetailView.as_view(), name='userprofile-detail'),
    url(r'^(?P<user>' + NAMESPACE_PATTERN + ')/reactivate/$', UserReactivateView.as_view(), name='userprofile-reactivate'),
    url(r'^(?P<user>' + NAMESPACE_PATTERN + ')/orgs/$', OrganizationListView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'user'}, name='userprofile-orgs'),
    url(r'^(?P<user>' + NAMESPACE_PATTERN + ')/sources/', include('sources.urls')),
    url(r'^(?P<user>' + NAMESPACE_PATTERN + ')/collections/', include('collection.urls')),
)

