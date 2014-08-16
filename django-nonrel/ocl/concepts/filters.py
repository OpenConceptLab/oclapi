from oclapi.filters import HaystackSearchFilter

__author__ = 'misternando'


class LimitSourceVersionFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(LimitSourceVersionFilter, self).get_filters(request, view)
        filters.update({'source_version':view.parent_resource_version.id})
        return filters

