import warnings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve
from django.db.models import Q
from django.http import Http404, HttpResponse
from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin
from rest_framework.response import Response
from oclapi.models import ResourceVersionModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from oclapi.permissions import HasPrivateAccess


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
    default_order_by = 'created_at'

    def is_verbose(self, request):
        return request.QUERY_PARAMS.get(self.verbose_param, False)

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())

        # Default is to allow empty querysets.  This can be altered by setting
        # `.allow_empty = False`, to raise 404 errors on empty querysets.
        if not self.allow_empty and not self.object_list:
            warnings.warn(
                'The `allow_empty` parameter is due to be deprecated. '
                'To use `allow_empty=False` style behavior, You should override '
                '`get_queryset()` and explicitly raise a 404 on empty querysets.',
                PendingDeprecationWarning
            )
            class_name = self.__class__.__name__
            error_msg = self.empty_error % {'class_name': class_name}
            raise Http404(error_msg)

        # Switch between paginated or standard style responses
        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list, many=True)

        return Response(serializer.data, headers=serializer.headers)


class BaseAPIView(generics.GenericAPIView):
    """
    An extension of generics.GenericAPIView that:
    1. Adds a hook for a post-initialize step
    2. De-couples the lookup field name (in the URL) from the "filter by" field name (in the queryset)
    3. Performs a soft delete on destroy()
    """
    pk_field = 'mnemonic'
    user_is_self = False

    def initial(self, request, *args, **kwargs):
        super(BaseAPIView, self).initial(request, *args, **kwargs)
        self.initialize(request, request.path_info, **kwargs)

    def initialize(self, request, path_info_segment, **kwargs):
        self.user_is_self = kwargs.pop('user_is_self', False)

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

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubResourceMixin(BaseAPIView, PathWalkerMixin):
    """
    Base view for a sub-resource.
    Includes a post-initialize step that determines the parent resource,
    and a get_queryset method that applies the appropriate permissions and filtering.
    """
    user = None
    userprofile = None
    user_is_self = False
    parent_path_info = None
    parent_resource = None
    base_or_clause = []

    def initialize(self, request, path_info_segment, **kwargs):
        super(SubResourceMixin, self).initialize(request, path_info_segment, **kwargs)
        self.user = request.user
        if self.user and hasattr(self.user, 'get_profile'):
            self.userprofile = self.user.get_profile()
        if self.user_is_self and self.userprofile:
            self.parent_resource = self.userprofile
        else:
            levels = 1 if isinstance(self, ListModelMixin) or isinstance(self, CreateModelMixin) else 2
            self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=levels)
            self.parent_resource = None
            if self.parent_path_info and '/' != self.parent_path_info:
                self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)


class ConceptDictionaryMixin(SubResourceMixin):
    base_or_clause = [Q(public_access=ACCESS_TYPE_EDIT), Q(public_access=ACCESS_TYPE_VIEW)]
    permission_classes = (HasPrivateAccess,)

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
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
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource = self.parent_resource.versioned_object
            parent_resource_type = ContentType.objects.get_for_model(self.parent_resource)
            queryset = queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=self.parent_resource.id)
        return queryset


class ConceptDictionaryCreateMixin(ConceptDictionaryMixin):

    """
    Concrete view for creating a model instance.
    """
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, owner=request.user, parent_resource=self.parent_resource)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                serializer = self.get_detail_serializer(self.object, data=request.DATA, files=request.FILES, partial=True)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_success_headers(self, data):
        try:
            return {'Location': data['url']}
        except (TypeError, KeyError):
            return {}


class ConceptDictionaryUpdateMixin(ConceptDictionaryMixin):

    """
    Concrete view for updating a model instance.
    """
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self.parent_resource:
            return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        self.object = self.get_object()
        created = False
        save_kwargs = {'force_update': True, 'parent_resource': self.parent_resource}
        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=True)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=created)
                serializer = self.get_detail_serializer(self.object)
                return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_detail_serializer(self, obj, data=None, files=None, partial=False):
        pass


class ChildResourceMixin(SubResourceMixin):

    def get_queryset(self):
        queryset = super(ChildResourceMixin, self).get_queryset()
        if self.parent_resource:
            # If we have a parent resource at this point, then the implication is that we have access to that resource
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource = self.parent_resource.versioned_object
            parent_resource_type = ContentType.objects.get_for_model(self.parent_resource)
            queryset = queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=self.parent_resource.id)
        return queryset


class VersionedResourceChildMixin(ConceptDictionaryMixin):
    """
    Base view for a sub-resource that is a child of a versioned resource.
    For example, a Concept is a child of a Source, which can be versioned.
    Includes a post-initialize step that determines the parent resource,
    and a get_queryset method that limits the scope to children of the versioned resource.
    """
    parent_resource_version = None
    parent_resource_version_model = None
    child_list_attribute = None

    def initialize(self, request, path_info_segment, **kwargs):
        levels = 1 if self.model.get_url_kwarg() in kwargs else 0
        levels = levels + 1 if isinstance(self, ListModelMixin) or isinstance(self, CreateModelMixin) else levels + 2
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=levels)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)

    def get_queryset(self):
        all_children = getattr(self.parent_resource_version, self.child_list_attribute) or []
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        queryset = queryset.filter(id__in=all_children)
        return queryset


class ResourceVersionMixin(BaseAPIView, PathWalkerMixin):
    """
    Base view for a resource that is a version of another resource (e.g. a SourceVersion).
    Includes a post-initialize step that determines the versioned object, and a get_queryset method
    that limits the scope to versions of that object.
    """
    versioned_object_path_info = None
    versioned_object = None

    def initialize(self, request, path_info_segment, **kwargs):
        super(ResourceVersionMixin, self).initialize(request, path_info_segment, **kwargs)
        self.versioned_object_path_info = self.get_parent_in_path(path_info_segment)
        self.versioned_object = self.get_object_for_path(self.versioned_object_path_info, request)

    def get_queryset(self):
        queryset = super(ResourceVersionMixin, self).get_queryset()
        versioned_object_type = ContentType.objects.get_for_model(self.versioned_object)
        queryset = queryset.filter(versioned_object_type__pk=versioned_object_type.id, versioned_object_id=self.versioned_object.id)
        return queryset


class ResourceAttributeChildMixin(BaseAPIView, PathWalkerMixin):
    """
    Base view for (a) child(ren) of a resource version.
    Currently, the only instances of this view are:
    GET [collection parent]/collections/:collection/:version/children
    GET [source parent]/sources/:source/:version/children
    """
    resource_version_path_info = None
    resource_version = None

    def initialize(self, request, path_info_segment, **kwargs):
        super(ResourceAttributeChildMixin, self).initialize(request, path_info_segment, **kwargs)
        self.resource_version_path_info = self.get_parent_in_path(path_info_segment)
        self.resource_version = self.get_object_for_path(self.resource_version_path_info, request)
