from oclapi.filters import HaystackSearchFilter
from django.contrib.auth.models import AnonymousUser

class OrgSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(OrgSearchFilter, self).get_filters(request, view)

        if isinstance(request.user, AnonymousUser):
            filters.update({'public_can_view': True})
        #elif not request.user.is_staff:
            #should also search across request.user.get_profile().organizations but I failed to make it work so far
            #filters.update({'public_can_view': True})

        return filters