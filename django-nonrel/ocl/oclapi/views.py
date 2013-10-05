from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve
from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from users.models import UserProfile


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


class SubResourceMixin(generics.GenericAPIView):
    user_is_self = False

    def initial(self, request, *args, **kwargs):
        super(SubResourceMixin, self).initial(request, *args, **kwargs)
        if kwargs.pop('user_is_self', False):
            self.user_is_self = True
            self.parent_resource = request.user.get_profile()
            self.parent_resource_type = UserProfile
        else:
            self.path_info = request.path_info
            self.related_name = kwargs.pop('related_name', None)

    def get_parent_resource(self):
        last_index = len(self.path_info) - 1
        last_slash = self.path_info.rindex('/')
        if last_slash == last_index:
            last_slash = self.path_info.rindex('/', 0, last_index)
        path_prefix = self.path_info[0:last_slash]
        if not isinstance(self, ListModelMixin) and not isinstance(self, CreateModelMixin):
            last_slash = path_prefix.rindex('/')
            path_prefix = path_prefix[0:last_slash]
        parent_path = path_prefix + '/'
        callback, callback_args, callback_kwargs = resolve(parent_path)
        view = callback.cls(request=self.request, kwargs=callback_kwargs)
        return view.get_object()

    def get_queryset(self):
        queryset = super(SubResourceMixin, self).get_queryset()
        parent_resource = self.get_parent_resource()
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        return queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id)

