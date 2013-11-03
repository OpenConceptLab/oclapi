from oclapi.permissions import HasPrivateAccess
from sources.models import EDIT_ACCESS_TYPE, VIEW_ACCESS_TYPE


class CanViewCollection(HasPrivateAccess):
    """
    The request is authenticated as a user, and the user can view this source
    """

    def has_object_permission(self, request, view, obj):
        if EDIT_ACCESS_TYPE == obj.public_access or VIEW_ACCESS_TYPE == obj.public_access:
            return True
        return super(CanViewCollection, self).has_object_permission(request, view, obj)


class CanEditCollection(HasPrivateAccess):
    """
    The request is authenticated as a user, and the user can edit this source
    """

    def has_object_permission(self, request, view, obj):
        if EDIT_ACCESS_TYPE == obj.public_access:
            return True
        return super(CanEditCollection, self).has_object_permission(request, view, obj)
