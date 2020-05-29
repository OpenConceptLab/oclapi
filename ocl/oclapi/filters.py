import re
import urllib

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from haystack.inputs import Raw, Not
from haystack.query import RelatedSearchQuerySet, SearchQuerySet
from rest_framework.filters import BaseFilterBackend

from oclapi.models import ACCESS_TYPE_NONE
from oclapi.search_indexes import encode_search_field_name
from orgs.models import Organization
from users.models import UserProfile


class SearchQuerySetWrapper(object):

    def __init__(self, sqs, limit_iter=True):
        self.sqs = sqs
        self.sqs._fill_cache(0, settings.HAYSTACK_ITERATOR_LOAD_PER_QUERY or 25)
        self.limit_iter = limit_iter
        self.facets = sqs.facet_counts()

    def __len__(self):
        return len(self.sqs)

    def __getitem__(self, item):
        result = self.sqs.__getitem__(item)
        if isinstance(result, list):
            return [r.object for r in result]
        return result.object

    def __iter__(self):
        iteration = self.sqs[0:10] if self.limit_iter else self.sqs
        for result in iteration:
            yield result.object


class BaseHaystackSearchFilter(BaseFilterBackend):
    search_param = 'q'  # The URL query parameter used for the search.
    sort_asc_param = 'sortAsc'
    sort_desc_param = 'sortDesc'

    def get_search_query(self, request):
        """
        Search terms are set by a ?q=... query parameter,
        and may be expressed using the full Lucene query syntax
        """
        return request.QUERY_PARAMS.get(self.search_param, '')

    def get_facets(self, request, view):
        facets = []
        include_facets = request.META.get('HTTP_INCLUDEFACETS', False)
        if include_facets:
            for k, v in view.solr_fields.iteritems():
                if v.get('facet', False):
                    facets.append(k)
        return facets

    def get_filters(self, request, view):
        filters = {}
        if not view.solr_fields:
            return filters
        for k in request.QUERY_PARAMS:
            v = request.QUERY_PARAMS.get(k,'')
            if k in view.solr_fields:
                attrs = view.solr_fields[k]
                if attrs.get('filterable', False):
                    vals = v.split(',')
                    clause = "(%s)" % ' OR '.join(vals)
                    filters["%s__exact" % k] = Raw(clause)
            if k.startswith('extras__'):
                #encode extras name
                field_name_parts = []
                for part in k.split('__'):
                    encoded = encode_search_field_name(part)
                    field_name_parts.append(encoded)
                field_name = '_'.join(field_name_parts)
                vals = v.split(',')
                clause = "(%s)" % ' OR '.join(vals)
                if field_name.endswith('_21'): #ends with '!'
                    filters["-%s__exact" % field_name[:-3]] = Raw(clause)
                else:
                    filters["%s__exact" % field_name] = Raw(clause)

        return filters

    def get_sq_filters(self, request, view):
        filters = []
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

    def _filter_queryset(self, request, queryset, view, sqs):
        use_sqs = False
        facets = self.get_facets(request, view)
        use_sqs = use_sqs or facets
        search_query = self.get_search_query(request)
        use_sqs = use_sqs or search_query
        filters = self.get_filters(request, view)
        use_sqs = use_sqs or filters
        sq_filters = self.get_sq_filters(request, view)
        use_sqs = use_sqs or sq_filters
        sort, desc = self.get_sort_and_desc(request)
        if sort:
            sort = sort if self.is_valid_sort(sort, view) else None
            if sort and desc:
                sort = '-' + sort
        use_sqs = use_sqs or sort
        if use_sqs:
            if search_query:
                sqs = sqs.filter(content=Raw("(%s)" % search_query))
            for f in facets:
                sqs = sqs.facet(f)
            if hasattr(view, 'default_filters'):
                filters.update(view.default_filters)
            if filters:
                sqs = sqs.filter(**filters)
            if sq_filters:
                for sq_filter in sq_filters:
                    sqs = sqs.filter(sq_filter)
            if sort:
                sqs = sqs.order_by(sort)
            else:
                default_sort = self.get_default_sort(view)
                if default_sort:
                    sqs = sqs.order_by(default_sort)
            sqs = sqs.models(view.model)
            if hasattr(sqs, 'load_all_queryset'):
                sqs = sqs.load_all().load_all_queryset(view.model, queryset)
            return SearchQuerySetWrapper(sqs)

        if hasattr(view, 'default_order_by'):
            queryset = queryset.order_by(view.default_order_by)
        return queryset


class HaystackSearchFilter(BaseHaystackSearchFilter):
    def filter_queryset(self, request, queryset, view):
        return self._filter_queryset(request, queryset, view, SearchQuerySet())


class ConceptContainerPermissionedSearchFilter(HaystackSearchFilter):
    def filter_queryset(self, request, queryset, view):
        current_user = request.user
        permissioned_qs = None

        if current_user.is_staff:
            permissioned_qs = queryset
        elif not current_user.is_anonymous():
            user_profile = UserProfile.objects.get(user=current_user)
            permissioned_qs = queryset.filter(
                Q(parent_id=user_profile.id, parent_type=ContentType.objects.get_for_model(UserProfile)) |
                Q(parent_id__in=user_profile.organizations, parent_type=ContentType.objects.get_for_model(Organization)) |
                ~Q(public_access=ACCESS_TYPE_NONE)
            )
        else:
            permissioned_qs = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))

        return super(ConceptContainerPermissionedSearchFilter, self)._filter_queryset(request, permissioned_qs, view, RelatedSearchQuerySet())
