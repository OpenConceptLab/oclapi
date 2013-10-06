from rest_framework.permissions import BasePermission
from orgs.models import Organization
from users.models import UserProfile


class HasOwnership(BasePermission):
    """
    The request is authenticated as a user, and the user is a member of the referenced organization
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            if isinstance(obj, UserProfile):
                return obj.user == request.user
            elif isinstance(obj, Organization):
                return request.user.username in obj.members
            return True
        return False
