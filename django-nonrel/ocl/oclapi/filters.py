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

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.QUERY_PARAMS.get(self.search_param, '')
        return params.replace(',', ' ').split()

    def construct_search(self, field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    def filter_queryset(self, request, queryset, view):
        terms = self.get_search_terms(request)
        if terms:
            sqs = RelatedSearchQuerySet()
            for term in terms:
                sqs = sqs.filter(content=term)
            sqs = sqs.load_all()
            sqs = sqs.load_all_queryset(view.model, queryset)
            return SearchQuerySetWrapper(sqs)
        return queryset
