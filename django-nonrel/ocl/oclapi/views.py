from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve
from django.db.models import Q
from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin


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
    base_or_clause = []

    def initial(self, request, *args, **kwargs):
        super(SubResourceMixin, self).initial(request, *args, **kwargs)
        self.parent_path_info = self._get_parent_path_info(request)
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

    def _get_parent_path_info(self, request):
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
        return path_prefix

    def _get_parent_resource(self):
        if self.parent_path_info is None:
            return None
        callback, callback_args, callback_kwargs = resolve(self.parent_path_info)
        view = callback.cls(request=self.request, kwargs=callback_kwargs)
        parent = view.get_object()
        return parent


class ResourceVersionMixin(BaseAPIView):
    versioned_object_path_info = None
    versioned_object = None

    def initial(self, request, *args, **kwargs):
        super(ResourceVersionMixin, self).initial(request, *args, **kwargs)
        self.versioned_object_path_info = self._get_versioned_object_path_info(request)
        self.versioned_object = self._get_versioned_object()

    def get_queryset(self):
        queryset = super(ResourceVersionMixin, self).get_queryset()
        versioned_object_type = ContentType.objects.get_for_model(self.versioned_object)
        queryset = queryset.filter(versioned_object_type__pk=versioned_object_type.id, versioned_object_id=self.versioned_object.id)
        return queryset

    def _get_versioned_object_path_info(self, request):
        path_info = request.path_info
        last_index = len(path_info) - 1
        last_slash = path_info.rindex('/')
        if last_slash == last_index:
            last_slash = path_info.rindex('/', 0, last_index)
        return path_info[0:last_slash+1]

    def _get_versioned_object(self):
        callback, callback_args, callback_kwargs = resolve(self.versioned_object_path_info)
        view = callback.cls(request=self.request, kwargs=callback_kwargs)
        return view.get_object()
