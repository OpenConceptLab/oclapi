__author__ = 'snyaggarwal'

from oclapi.filters import HaystackSearchFilter


class CollectionSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(CollectionSearchFilter, self).get_filters(request, view)
        if view.parent_resource:
            filters.update({'owner': view.parent_resource.mnemonic})
            filters.update({'ownerType': view.parent_resource.resource_type()})
        else:
            filters.update({'public_can_view': True})

        return filters
