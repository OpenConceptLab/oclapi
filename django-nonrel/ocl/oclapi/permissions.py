from rest_framework.permissions import BasePermission


class IsOrganizationMember(BasePermission):
    """
    The request is authenticated as a user, and the user is a member of the referenced organization
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            try:
                return obj.mnemonic in request.user.get_profile().organizations
            except:
                pass
        return False
