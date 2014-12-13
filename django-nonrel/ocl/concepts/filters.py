from oclapi.filters import SimpleHaystackSearchFilter

__author__ = 'misternando'


class PublicConceptsSearchFilter(SimpleHaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicConceptsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        if not view.include_retired:
            filters.update({'retired': False})
        return filters


class LimitSourceVersionFilter(SimpleHaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(LimitSourceVersionFilter, self).get_filters(request, view)
        filters.update({'source_version': view.parent_resource_version.id})
        if not view.include_retired:
            filters.update({'retired': False})
        return filters

