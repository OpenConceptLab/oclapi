import dateutil.parser

__author__ = 'misternando'

DEFAULT_LIMIT = 30


class FeedFilterMixin(object):

    def filter_queryset(self, qs):
        if self.updated_since:
            updated_since_date = dateutil.parser.parse(self.updated_since)
            qs = qs.filter(updated_at__gte=updated_since_date)
        qs = qs.order_by('-updated_at')
        if self.limit is None:
            qs = qs[:DEFAULT_LIMIT]
        else:
            limit = int(self.limit)
            if limit > 0:
                qs = qs[:limit]
        return qs
