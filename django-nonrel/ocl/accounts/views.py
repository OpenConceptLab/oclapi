from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from rest_framework import viewsets
from accounts.models import UserProfile
from accounts.serializers import UserSerializer, GroupSerializer


def current_user(request):
    mapping = {
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
    }
    view = UserViewSet.as_view(actions=mapping, suffix='Instance')
    return view(request)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer

    def get_object(self, queryset=None):
        shortcut_url = reverse('accounts.views.current_user')
        if self.request.path == shortcut_url:
            return self.request.user.get_profile()
        return super(UserViewSet, self).get_object()


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer