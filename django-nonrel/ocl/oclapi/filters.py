from haystack.query import RelatedSearchQuerySet
from rest_framework.filters import BaseFilterBackend


class SearchQuerySetWrapper(object):

    def __init__(self, sqs):
        self.sqs = sqs
        self.sqs._fill_cache(0,10)

    def __len__(self):
        return len(self.sqs)

    def __getitem__(self, item):
        result = self.sqs.__getitem__(item)
        if isinstance(result, list):
            return [r.object for r in result]
        return result.object

    def __iter__(self):
        yield self.sqs.__iter__().object


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

    def get_filters(self, request, view):
        filters = {}
        if not view.solr_fields:
            return filters
        for k in request.QUERY_PARAMS:
            v = request.QUERY_PARAMS.get(k,'')
            if k in view.solr_fields:
                attrs = view.solr_fields[k]
                if attrs.get('filterable', False):
                    filters["%s__exact" % k] = v
        return filters

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

    def get_default_sort(self, view):
        for field in view.solr_fields:
            attrs = view.solr_fields[field]
            if 'sortable' in attrs and 'default' in attrs:
                prefix = '-' if 'desc' == attrs['default'] else ''
                return prefix + field
        return None

    def filter_queryset(self, request, queryset, view):
        use_sqs = False
        terms = self.get_search_terms(request)
        use_sqs |= len(terms)
        filters = self.get_filters(request, view)
        use_sqs |= len(filters)
        sort, desc = self.get_sort_and_desc(request)
        if sort:
            sort = sort if self.is_valid_sort(sort, view) else None
            if sort and desc:
                sort = '-' + sort
        use_sqs |= sort is not None
        if use_sqs:
            sqs = RelatedSearchQuerySet()
            for term in terms:
                sqs = sqs.filter(content=term)
            if filters:
                sqs = sqs.filter(**filters)
            if sort:
                sqs = sqs.order_by(sort)
            else:
                default_sort = self.get_default_sort(view)
                if default_sort:
                    sqs = sqs.order_by(default_sort)
            sqs = sqs.models(view.model)
            sqs = sqs.load_all()
            sqs = sqs.load_all_queryset(view.model, queryset)
            return SearchQuerySetWrapper(sqs)

        if hasattr(view, 'default_order_by'):
            return queryset.order_by(view.default_order_by)
        else:
            return queryset
