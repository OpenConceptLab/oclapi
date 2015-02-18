from haystack.backends import SQ
from haystack.query import RelatedSearchQuerySet
from oclapi.filters import HaystackSearchFilter, SearchQuerySetWrapper

__author__ = 'misternando'


class MappingSearchFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        sqs = []
        map_type = request.QUERY_PARAMS.get('mapType','')
        if map_type:
            sqs.append(SQ(map_type__exact=map_type))

        source = request.QUERY_PARAMS.get('source', '')
        source_sqs = []
        if source:
            sources = source.split(',')
            for s in sources:
                source_sqs.append(SQ(from_source__exact=s))
                source_sqs.append(SQ(to_source__exact=s))
        if source_sqs:
            sqs.append(reduce(lambda x, y: x | y, source_sqs[1:], source_sqs[0]))

        from_source = request.QUERY_PARAMS.get('fromSource', '')
        from_source_sqs = []
        if from_source:
            sources = from_source.split(',')
            for s in sources:
                from_source_sqs.append(SQ(from_source__exact=s))
        if from_source_sqs:
            sqs.append(reduce(lambda x, y: x | y, from_source_sqs[1:], from_source_sqs[0]))

        to_source = request.QUERY_PARAMS.get('toSource', '')
        to_source_sqs = []
        if to_source:
            sources = to_source.split(',')
            for s in sources:
                to_source_sqs.append(SQ(to_source__exact=s))
        if to_source_sqs:
            sqs.append(reduce(lambda x, y: x | y, to_source_sqs[1:], to_source_sqs[0]))

        concept = request.QUERY_PARAMS.get('concept', '')
        concept_sqs = []
        if concept:
            concepts = concept.split(',')
            for c in concepts:
                concept_sqs.append(SQ(from_concept__exact=c))
                concept_sqs.append(SQ(to_concept__exact=c))
        if concept_sqs:
            sqs.append(reduce(lambda x, y: x | y, concept_sqs[1:], concept_sqs[0]))

        from_concept = request.QUERY_PARAMS.get('fromConcept', '')
        from_concept_sqs = []
        if from_concept:
            concepts = from_concept.split(',')
            for c in concepts:
                from_concept_sqs.append(SQ(from_concept__exact=c))
        if from_concept_sqs:
            sqs.append(reduce(lambda x, y: x | y, from_concept_sqs[1:], from_concept_sqs[0]))

        to_concept = request.QUERY_PARAMS.get('toConcept', '')
        to_concept_sqs = []
        if to_concept:
            concepts = to_concept.split(',')
            for c in concepts:
                to_concept_sqs.append(SQ(to_concept=c))
        if to_concept_sqs:
            sqs.append(reduce(lambda x, y: x | y, to_concept_sqs[1:], to_concept_sqs[0]))

        if not sqs:
            return sqs
        else:
            return reduce(lambda x, y: x & y, sqs[1:], sqs[0])

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
                sqs = sqs.filter(filters)
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
