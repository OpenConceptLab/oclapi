from orgs.models import Organization, ORG_OBJECT_TYPE
from oclapi.filters import HaystackSearchFilter
from django.contrib.auth.models import AnonymousUser
from haystack.query import SQ

from users.models import USER_OBJECT_TYPE


class CollectionSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(CollectionSearchFilter, self).get_filters(request, view)
        if view.parent_resource:
            filters.update({'owner': view.parent_resource.mnemonic})
            filters.update({'ownerType': view.parent_resource.resource_type()})

        if isinstance(request.user, AnonymousUser):
            filters.update({'public_can_view': True})

        return filters

    def get_sq_filters(self, request, view):
        filters = super(CollectionSearchFilter, self).get_sq_filters(request, view)

        if not isinstance(request.user, AnonymousUser) and not request.user.is_staff:
            org_ids = request.user.get_profile().organizations
            if org_ids:
                orgs = Organization.objects.filter(id__in = org_ids).values_list('mnemonic', flat=True)
                filters.append(SQ(public_can_view=True)
                               | (SQ(owner__exact=request.user.get_profile().mnemonic) & SQ(ownerType__exact=USER_OBJECT_TYPE))
                               | (SQ(owner__in=orgs) & SQ(ownerType__exact=ORG_OBJECT_TYPE)))
            else:
                filters.append(SQ(public_can_view=True))

        return filters
