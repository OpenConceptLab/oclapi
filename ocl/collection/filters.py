from oclapi.filters import ConceptContainerPermissionedSearchFilter
from django.contrib.auth.models import AnonymousUser

from users.models import USER_OBJECT_TYPE


class CollectionSearchFilter(ConceptContainerPermissionedSearchFilter):
    def get_filters(self, request, view):
        filters = super(CollectionSearchFilter, self).get_filters(request, view)

        user = request.QUERY_PARAMS.get('user', None)
        if user:
            filters.update({'owner': user, 'ownerType': USER_OBJECT_TYPE})

        if view.parent_resource:
            filters.update({'owner': view.parent_resource.mnemonic})
            filters.update({'ownerType': view.parent_resource.resource_type()})

        if isinstance(request.user, AnonymousUser):
            filters.update({'public_can_view': True})

        return filters
