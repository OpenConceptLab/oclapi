import dateutil.parser

__author__ = 'misternando'


class FeedFilterMixin(object):

    def filter_queryset(self, qs):
        if self.updated_since:
            updated_since_date = dateutil.parser.parse(self.updated_since)
            qs = qs.filter(updated_at__gte=updated_since_date)
        limit = self.limit or 30
        qs = qs[:limit]
        return qs.order_by('-updated_at')
