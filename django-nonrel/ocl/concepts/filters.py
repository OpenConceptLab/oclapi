from oclapi.filters import SimpleHaystackSearchFilter

__author__ = 'misternando'


class PublicConceptsSearchFilter(SimpleHaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicConceptsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        return filters


class LimitSourceVersionFilter(SimpleHaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(LimitSourceVersionFilter, self).get_filters(request, view)
        filters.update({'source_version': view.parent_resource_version.id})
        return filters

