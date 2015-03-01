from oclapi.filters import HaystackSearchFilter

__author__ = 'misternando'


class PublicMappingsSearchFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicMappingsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        return filters


class SourceRestrictedMappingsFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(SourceRestrictedMappingsFilter, self).get_filters(request, view)
        filters.update({'source_version': view.parent_resource_version.id})
        return filters