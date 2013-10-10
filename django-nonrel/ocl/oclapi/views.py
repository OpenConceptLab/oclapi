from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve
from django.db.models import Q
from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from orgs.models import Organization


class BaseAPIView(generics.GenericAPIView):
    pk_field = 'mnemonic'

    def get_object(self, queryset=None):
        # Determine the base queryset to use.
        if queryset is None:
            queryset = self.filter_queryset(self.get_queryset())
        else:
            pass  # Deprecation warning

        # Perform the lookup filtering.
        lookup = self.kwargs.get(self.lookup_field, None)
        filter_kwargs = {self.pk_field: lookup}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class SubResourceMixin(BaseAPIView):
    user = None
    userprofile = None
    user_is_self = False
    parent_path_info = None
    parent_resource = None
    parent_resource_url = None
    base_or_clause = []

    def initial(self, request, *args, **kwargs):
        super(SubResourceMixin, self).initial(request, *args, **kwargs)
        self.parent_path_info, self.parent_resource_url = self._get_parent_path_and_url(request)
        self.user = request.user
        if self.user and hasattr(self.user, 'get_profile'):
            self.userprofile = self.user.get_profile()
        if kwargs.pop('user_is_self', False):
            self.user_is_self = True
            self.parent_resource = request.user.get_profile()
        else:
            self.parent_resource = self._get_parent_resource()

    def get_queryset(self):
        queryset = super(SubResourceMixin, self).get_queryset()
        or_clauses = []
        if self.user:
            or_clauses.append(Q(owner=self.user))
        if self.userprofile:
            or_clauses += map(lambda x: Q(parent_id=x), self.userprofile.organizations)
        or_clauses += self.base_or_clause
        if or_clauses:
            if len(or_clauses) > 1:
                queryset = queryset.filter(reduce(lambda x, y: x | y, or_clauses[1:], or_clauses[0]))
            else:
                queryset = queryset.filter(or_clauses[0])
        if self.parent_resource:
            parent_resource_type = ContentType.objects.get_for_model(self.parent_resource)
            queryset = queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=self.parent_resource.id)
        return queryset

    def get_serializer_context(self):
        context = super(SubResourceMixin, self).get_serializer_context()
        context.update({'parent_resource_url': self.parent_resource_url})
        return context

    def _get_parent_path_and_url(self, request):
        path_info = request.path_info
        last_index = len(path_info) - 1
        last_slash = path_info.rindex('/')
        if last_slash == last_index:
            last_slash = path_info.rindex('/', 0, last_index)
        path_prefix = path_info[0:last_slash]
        if not isinstance(self, ListModelMixin) and not isinstance(self, CreateModelMixin):
            last_slash = path_prefix.rindex('/')
            path_prefix = path_prefix[0:last_slash]
        if path_prefix:
            path_prefix += '/'
            return path_prefix, request.build_absolute_uri(path_prefix)
        else:
            return None, None

    def _get_parent_resource(self):
        if self.parent_path_info is None:
            return None
        callback, callback_args, callback_kwargs = resolve(self.parent_path_info)
        view = callback.cls(request=self.request, kwargs=callback_kwargs)
        parent = view.get_object()
        #self.check_object_permissions(self.request, parent)
        return parent

