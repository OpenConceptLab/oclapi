from django.conf.urls.defaults import patterns, url, include
from orgs.views import OrganizationListView
from users.models import UserProfile
from users.views import UserListView, UserDetailView, UserReactivateView, UserLoginView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', UserListView.as_view(), name='userprofile-list'),
    url(r'^login/$', UserLoginView.as_view(), name='user-login'),
    url(r'^(?P<user>[a-zA-Z0-9\-\.]+)/$', UserDetailView.as_view(), name='userprofile-detail'),
    url(r'^(?P<user>[a-zA-Z0-9\-\.]+)/reactivate/$', UserReactivateView.as_view(), name='userprofile-reactivate'),
    url(r'^(?P<user>[a-zA-Z0-9\-\.]+)/orgs/$', OrganizationListView.as_view(), {'related_object_type': UserProfile, 'related_object_kwarg': 'user'}, name='userprofile-orgs'),
    url(r'^(?P<user>[a-zA-Z0-9\-\.]+)/sources/', include('sources.urls')),
    url(r'^(?P<user>[a-zA-Z0-9\-\.]+)/collections/', include('collection.urls')),
)

