from django.conf.urls.defaults import patterns, url
from users.views import UserListView, UserRUDView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', UserListView.as_view(), name='userprofile-list'),
    url(r'^(?P<mnemonic>[a-zA-Z0-9\-]+)/$', UserRUDView.as_view(), name='userprofile-detail'),
)

