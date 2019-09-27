__author__ = 'snyaggarwal'

from oclapi.filters import HaystackSearchFilter
from django.contrib.auth.models import AnonymousUser


class CollectionSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(CollectionSearchFilter, self).get_filters(request, view)
        if view.parent_resource:
            filters.update({'owner': view.parent_resource.mnemonic})
            filters.update({'ownerType': view.parent_resource.resource_type()})

        if isinstance(request.user, AnonymousUser) or (not request.user.is_staff and view.parent_resource.id not in request.user.get_profile().organizations):
            filters.update({'public_can_view': True})

        return filters
