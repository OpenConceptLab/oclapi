from django.core.urlresolvers import resolve
from oclapi.utils import compact, write_csv_to_s3, get_csv_from_s3
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from oclapi.utils import compact, extract_values
from users.models import UserProfile

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
            filename = '_'.join(compact(path.split('/')))
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
        return UserProfile.objects.get(mnemonic=requesting_user).id in parent.owner.members

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
                                            'descriptions', 'created_by', 'updated_by', 'created_at', 'updated_at')

        for value in values:
            names = value.get('names')
            descriptions = value.get('descriptions')

            value['names'] = self.join_values(names)
            value['descriptions'] = self.join_values(descriptions)

            preferred_name = self.preferred_name(names)
            value['display_name'] = preferred_name.get('name')
            value['display_locale'] = preferred_name.get('locale')

        values.field_names.extend(['display_name', 'display_locale'])
        return values

    def join_values(self, objects):
        localize_text_keys = ['name', 'locale', 'type']
        return ', '.join(
            map(lambda obj: ' '.join(compact(extract_values(obj[1], localize_text_keys))), objects))

    def preferred_name(self, names):
        return next((name for name in names if name[1].get('locale_preferred')), [None, {'name': '', 'locale': ''}])[1]
