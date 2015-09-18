from oclapi.filters import SimpleHaystackSearchFilter

__author__ = 'misternando'


class ConceptSearchFilter(SimpleHaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(ConceptSearchFilter, self).get_filters(request, view)
        if view.updated_since:
            filters.update({'last_update__gte': view.updated_since})
        if not view.include_retired:
            filters.update({'retired': False})
        return filters


class PublicConceptsSearchFilter(ConceptSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicConceptsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        return filters


class LimitSourceVersionFilter(ConceptSearchFilter):

    def get_filters(self, request, view):
        filters = super(LimitSourceVersionFilter, self).get_filters(request, view)
        filters.update({'source_version': view.parent_resource_version.id})
        return filters
