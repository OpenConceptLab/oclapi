from haystack.query import RelatedSearchQuerySet
from rest_framework.filters import BaseFilterBackend


class SearchQuerySetWrapper(object):

    def __init__(self, sqs):
        self.sqs = sqs

    def __len__(self):
        return len(self.sqs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return [i.object for i in self.sqs.__getitem__(item)]
        return self.sqs.__getitem__(item).object

    def __iter__(self):
        for item in self.sqs:
            yield item.object  # This is the line that gets the model instance out of the Search object


class HaystackSearchFilter(BaseFilterBackend):
    search_param = 'q'  # The URL query parameter used for the search.
    sort_asc_param = 'sortAsc'
    sort_desc_param = 'sortDesc'

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.QUERY_PARAMS.get(self.search_param, '')
        return params.replace(',', ' ').split()

    def get_sort_and_desc(self, request):
        sort_field = request.QUERY_PARAMS.get(self.sort_desc_param)
        if sort_field is not None:
            return sort_field, True
        sort_field = request.QUERY_PARAMS.get(self.sort_asc_param)
        if sort_field is not None:
            return sort_field, False
        return None, None

    def construct_search(self, field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    def is_valid_sort(self, field, view):
        if not view.solr_fields:
            return False
        if field in view.solr_fields:
            attrs = view.solr_fields[field]
            return attrs.get('sortable', False)
        return False

    def filter_queryset(self, request, queryset, view):
        terms = self.get_search_terms(request)
        sort, desc = self.get_sort_and_desc(request)
        if sort:
            sort = sort if self.is_valid_sort(sort, view) else None
            if sort and desc:
                sort = '-' + sort
        if terms or sort:
            sqs = RelatedSearchQuerySet()
            for term in terms:
                sqs = sqs.filter(content=term)
            if sort:
                sqs = sqs.order_by(sort)
            sqs = sqs.load_all()
            sqs = sqs.load_all_queryset(view.model, queryset)
            return SearchQuerySetWrapper(sqs)

        return queryset
