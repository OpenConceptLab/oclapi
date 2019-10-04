from oclapi.filters import HaystackSearchFilter
from django.contrib.auth.models import AnonymousUser
from haystack.query import SQ

class OrgSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(OrgSearchFilter, self).get_filters(request, view)

        if isinstance(request.user, AnonymousUser):
            filters.update({'public_can_view': True})
        #elif not request.user.is_staff:
            #should also search across request.user.get_profile().organizations but I failed to make it work so far
            #filters.update({'public_can_view': True})

        return filters

    def get_sq_filters(self, request, view):
        filters = super(OrgSearchFilter, self).get_sq_filters(request, view)

        if not isinstance(request.user, AnonymousUser) and not request.user.is_staff:
            org_ids = request.user.get_profile().organizations
            unicode_ids = []
            for org_id in org_ids:
                unicode_ids.append(u'orgs.organization.%s' % org_id)
            if org_ids:
                filters.append(SQ(public_can_view=True) | SQ(id__in=unicode_ids))
            else:
                filters.append(SQ(public_can_view=True))

        return filters