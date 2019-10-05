from oclapi.filters import ConceptContainerPermissionedSearchFilter
from django.contrib.auth.models import AnonymousUser


class SourceSearchFilter(ConceptContainerPermissionedSearchFilter):
    def get_filters(self, request, view):
        filters = super(SourceSearchFilter, self).get_filters(request, view)
        if view.parent_resource:
            filters.update({'owner': view.parent_resource.mnemonic})
            filters.update({'ownerType': view.parent_resource.resource_type()})

        if isinstance(request.user, AnonymousUser):
            filters.update({'public_can_view': True})

        return filters
