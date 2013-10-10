from rest_framework.permissions import BasePermission
from orgs.models import Organization
from users.models import UserProfile


class HasOwnership(BasePermission):
    """
    The request is authenticated as a user, and the user is a member of the referenced organization
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'get_profile'):
            userprofile = request.user.get_profile()
            if isinstance(obj, UserProfile):
                return obj == userprofile
            elif isinstance(obj, Organization):
                return userprofile.id in obj.members
            return True
        return False


class HasPrivateAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.user == obj.owner:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'get_profile'):
            profile = request.user.get_profile()
            if obj.parent_id in profile.organizations:
                return True
        return False
