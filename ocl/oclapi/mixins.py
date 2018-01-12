from django.core.urlresolvers import resolve
from oclapi.utils import compact, write_csv_to_s3, get_csv_from_s3
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from oclapi.utils import compact, extract_values
from users.models import UserProfile
from oclapi.filters import SearchQuerySetWrapper

__author__ = 'misternando'

HEAD = 'HEAD'

class PathWalkerMixin():
    """
    A Mixin with methods that help resolve a resource path to a resource object
    """
    path_info = None

    def get_parent_in_path(self, path_info, levels=1):
        last_index = len(path_info) - 1
        last_slash = path_info.rindex('/')
        if last_slash == last_index:
            last_slash = path_info.rindex('/', 0, last_index)
        path_info = path_info[0:last_slash+1]
        if levels > 1:
            i = 1
            while i < levels:
                last_index = len(path_info) - 1
                last_slash = path_info.rindex('/', 0, last_index)
                path_info = path_info[0:last_slash+1]
                i += 1
        return path_info

    def get_object_for_path(self, path_info, request):
        callback, callback_args, callback_kwargs = resolve(path_info)
        view = callback.cls(request=request, kwargs=callback_kwargs)
        view.initialize(request, path_info, **callback_kwargs)
        return view.get_object()


class ListWithHeadersMixin(ListModelMixin):
    verbose_param = 'verbose'
    facets = None
    default_filters = {'is_active': True}
    object_list = None

    def is_verbose(self, request):
        return request.QUERY_PARAMS.get(self.verbose_param, False)

    def list(self, request, *args, **kwargs):
        is_csv = request.QUERY_PARAMS.get('csv', False)
        search_string = request.QUERY_PARAMS.get('type', None)
        exact_match = request.QUERY_PARAMS.get('exact_match', None)
        if not exact_match and is_csv:
            pattern = request.QUERY_PARAMS.get('q', None)
            if pattern:
                request.QUERY_PARAMS._mutable = True
                request.QUERY_PARAMS['q'] = "*" + request.QUERY_PARAMS['q'] + "*"

        if is_csv and not search_string:
            return self.get_csv(request)

        if self.object_list is None:
            self.object_list = self.filter_queryset(self.get_queryset())

        if is_csv and search_string:
            klass = type(self.object_list[0])
            queryset = klass.objects.filter(id__in=self.get_object_ids())
            return self.get_csv(request, queryset)

        # Skip pagination if compressed results are requested
        meta = request._request.META
        include_facets = meta.get('HTTP_INCLUDEFACETS', False)
        facets = None
        if include_facets and hasattr(self.object_list, 'facets'):
            facets = self.object_list.facets

        compress = meta.get('HTTP_COMPRESS', False)
        return_all = self.get_paginate_by() == 0
        skip_pagination = compress or return_all

        # Switch between paginated or standard style responses
        sorted_list = self.prepend_head(self.object_list) if len(self.object_list) > 0 else self.object_list

        if not skip_pagination:
            page = self.paginate_queryset(sorted_list)
            if page is not None:
                serializer = self.get_pagination_serializer(page)
                results = serializer.data
                if facets:
                    return Response({'results': results, 'facets': facets}, headers=serializer.headers)
                else:
                    return Response(results, headers=serializer.headers)

        limit = int(request.QUERY_PARAMS.get('limit'))

        if limit == 0 and isinstance(sorted_list, SearchQuerySetWrapper):
            sorted_list.limit_iter = False
            klass = sorted_list.sqs.query.models.copy().pop()
            sorted_list = klass.objects.filter(id__in=sorted_list.sqs.values_list('pk', flat=True)).select_related().all()

        serializer = self.get_serializer(sorted_list, many=True)

        results = serializer.data
        if facets:
            return Response({'results': results, 'facets': facets})
        else:
            return Response(results)

    def get_object_ids(self):
        self.object_list.limit_iter = False
        return map(lambda o: o.id, self.object_list[0:100])

    def get_csv(self, request, queryset=None):
        filename, url, prepare_new_file, is_member = None, None, True, False

        parent = self.get_parent()

        if parent:
            prepare_new_file = False
            user = request.QUERY_PARAMS.get('user', None)
            is_member = self._is_member(parent, user)

        try:
            path = request.__dict__.get('_request').path
            filename = '_'.join(compact(path.split('/'))).replace('.', '_')
            kwargs = {
                'filename': filename,
            }
        except Exception:
            kwargs = {}

        if filename and prepare_new_file:
            url = get_csv_from_s3(filename, is_member)

        if not url:
            queryset = queryset or self._get_query_set_from_view(is_member)
            data = self.get_csv_rows(queryset) if hasattr(self, 'get_csv_rows') else queryset.values()
            url = write_csv_to_s3(data, is_member, **kwargs)

        return Response({'url': url}, status=200)

    def _is_member(self, parent, requesting_user):
        if not parent or type(parent).__name__ in ['UserProfile', 'Organization']:
            return False

        owner = parent.owner
        return UserProfile.objects.get(mnemonic=requesting_user).id in owner.members if type(owner).__name__ == 'Organization' else requesting_user == parent.created_by

    def _get_query_set_from_view(self, is_member):
        return self.get_queryset() if is_member else self.get_queryset()[0:100]

    def get_parent(self):
        if hasattr(self, 'parent_resource'):
            parent = self.parent_resource
        elif hasattr(self, 'versioned_object'):
            parent = self.versioned_object
        else:
            parent = None

        return parent

    @staticmethod
    def prepend_head(objects):
        if len(objects) > 0 and hasattr(objects[0], 'mnemonic'):
            head_el = [el for el in objects if hasattr(el, 'mnemonic') and el.mnemonic == HEAD]
            if head_el:
                objects = head_el + [el for el in objects if el.mnemonic != HEAD]

        return objects

    @staticmethod
    def _reduce_func(prev, current):
        prev_version_ids = map(lambda v: v.versioned_object_id, prev)
        if current.versioned_object_id not in prev_version_ids:
            prev.append(current)
        return prev


class ConceptVersionCSVFormatterMixin():
    def get_csv_rows(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()

        values = queryset.values('id', 'external_id', 'uri', 'concept_class', 'datatype', 'retired', 'names',
                                            'descriptions', 'created_by', 'created_at')

        for value in values:
            concept_ver = self.model.objects.get(id=value.pop('id'))
            value['Owner'] = concept_ver.owner
            value['Source'] = concept_ver.parent_resource
            value['Concept ID']  = concept_ver.versioned_object.mnemonic

            names = value.pop('names')
            descriptions = value.pop('descriptions')

            preferred_name = self.preferred_name(names)
            value['Preferred Name'] = preferred_name.get('name')
            value['Preferred Name Locale'] = preferred_name.get('locale')
            value['Concept Class'] = value.pop('concept_class')
            value['Datatype'] = value.pop('datatype')
            value['Retired'] = value.pop('retired')
            value['Synonyms'] = self.get_formatted_values(names)
            value['Description'] = self.get_formatted_values(descriptions)
            value['External ID'] = value.pop('external_id')
            value['Last Updated'] = value.pop('created_at')
            value['Updated By'] = value.pop('created_by')
            value['URI'] = value.pop('uri')


        values.field_names.extend(['Owner','Source','Concept ID','Preferred Name','Preferred Name Locale','Concept Class','Datatype','Retired','Synonyms','Description'
                                      ,'External ID','Last Updated','Updated By','URI'])
        del values.field_names[0:10]
        return values

    def join_values(self, objects):
        localize_text_keys = ['name', 'locale', 'type']
        return ', '.join(
            map(lambda obj: ' '.join(compact(extract_values(obj[1], localize_text_keys))), objects))

    def preferred_name(self, names):
        return next((name for name in names if name[1].get('locale_preferred')), [None, {'name': '', 'locale': ''}])[1]

    def get_formatted_values(self, items):
        formated_synonym=[]
        if items:
            for item in items:
                formated_synonym.append((item[1].get('name') if 'name' in item[1] else '') + (' [' + item[1].get('type') + ']' if 'type' in item[1] and item[1].get('type') else '')
                                        + (' [' + item[1].get('locale') + ']' if 'locale' in item[1] and item[1].get('locale') else ''))
        return ';'.join(formated_synonym)

