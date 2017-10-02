import dateutil.parser
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseForbidden
from rest_framework import generics, status
from rest_framework.generics import get_object_or_404 as generics_get_object_or_404
from rest_framework.generics import RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.response import Response
from oclapi.mixins import PathWalkerMixin
from oclapi.models import ResourceVersionModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW, ACCESS_TYPE_NONE
from oclapi.permissions import HasPrivateAccess, CanEditConceptDictionary, CanViewConceptDictionary, HasOwnership
from users.models import UserProfile

UPDATED_SINCE_PARAM = 'updatedSince'


def get_object_or_404(queryset, **filter_kwargs):
    try:
        return generics_get_object_or_404(queryset, **filter_kwargs)
    except DatabaseError:
        raise Http404


def parse_updated_since_param(request):
    updated_since = request.QUERY_PARAMS.get(UPDATED_SINCE_PARAM)
    if updated_since:
        try:
            return dateutil.parser.parse(updated_since)
        except ValueError: pass
    return None


def parse_boolean_query_param(request, param, default=None):
    val = request.QUERY_PARAMS.get(param, default)
    if val is None:
        return None
    for b in [True, False]:
        if str(b).lower() == val.lower():
            return b
    return None


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
        if self.user_is_self:
            try:
                self.userprofile = self.user.get_profile()
                if self.userprofile:
                    self.parent_resource = self.userprofile
                    return
            except UserProfile.DoesNotExist: pass
        else:
            levels = self.get_level()
            self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=levels)
            self.parent_resource = None
            if self.parent_path_info and '/' != self.parent_path_info:
                self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)

    def get_level(self):
        levels = 1 if isinstance(self, ListModelMixin) or isinstance(self, CreateModelMixin) else 2
        return levels


class ConceptDictionaryMixin(SubResourceMixin):
    base_or_clause = [Q(public_access=ACCESS_TYPE_EDIT), Q(public_access=ACCESS_TYPE_VIEW)]
    permission_classes = (HasPrivateAccess,)

    def get_queryset(self):
        queryset = super(ConceptDictionaryMixin, self).get_queryset()
        parent_is_self = self.parent_resource and self.userprofile and self.parent_resource == self.userprofile
        if self.parent_resource:
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource = self.parent_resource.versioned_object
            parent_resource_type = ContentType.objects.get_for_model(self.parent_resource)
            queryset = queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=self.parent_resource.id)
        # below part is commented because this should be the part of permission , not queryset
        # if not(self.user.is_staff or parent_is_self):
        #     queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
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
        permission = HasOwnership()
        if not permission.has_object_permission(request, self, self.parent_resource):
            return HttpResponseForbidden()
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, parent_resource=self.parent_resource)
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


class ConceptDictionaryExtrasMixin(SubResourceMixin):
    levels = 1

    def initialize(self, request, path_info_segment, **kwargs):
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=self.levels)
        self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)


class ConceptDictionaryExtrasView(ConceptDictionaryExtrasMixin, ListAPIView):
    permission_classes = (CanViewConceptDictionary,)
    levels = 1

    def list(self, request, *args, **kwargs):
        extras = self.parent_resource_version.extras or {}
        return Response(extras)


class ConceptDictionaryExtraRetrieveUpdateDestroyView(ConceptDictionaryExtrasMixin, RetrieveUpdateDestroyAPIView):
    concept_dictionary_version_class = None
    permission_classes = (CanEditConceptDictionary,)
    levels = 2

    def initialize(self, request, path_info_segment, **kwargs):
        super(ConceptDictionaryExtraRetrieveUpdateDestroyView, self).initialize(request, path_info_segment, **kwargs)
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewConceptDictionary,)
        self.key = kwargs.get('extra')
        if not self.parent_resource_version.extras:
            self.parent_resource_version.extras = dict()
        self.extras = self.parent_resource_version.extras

    def retrieve(self, request, *args, **kwargs):
        if self.key in self.extras:
            return Response({self.key: self.extras[self.key]})
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        value = request.DATA.get(self.key)
        if not value:
            return Response(['Must specify %s param in body.' % self.key], status=status.HTTP_400_BAD_REQUEST)

        self.extras[self.key] = value
        self.parent_resource_version.update_comment = 'Updated extras: %s=%s.' % (self.key, value)
        self.concept_dictionary_version_class.persist_changes(self.parent_resource_version)
        return Response({self.key: self.extras[self.key]})

    def delete(self, request, *args, **kwargs):
        if self.key in self.extras:
            del self.extras[self.key]
            self.parent_resource_version.update_comment = 'Deleted extra %s.' % self.key
            self.concept_dictionary_version_class.persist_changes(self.parent_resource_version)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Not found."}, status.HTTP_404_NOT_FOUND)


class ChildResourceMixin(SubResourceMixin):

    def get_queryset(self):
        queryset = super(ChildResourceMixin, self).get_queryset()
        if self.parent_resource:
            # If we have a parent resource at this point, then the implication is that we have access to that resource
            if hasattr(self.parent_resource, 'versioned_object'):
                self.parent_resource = self.parent_resource.versioned_object
            parent_resource_type = ContentType.objects.get_for_model(self.parent_resource)
            queryset = queryset.filter(parent_type__pk=parent_resource_type.id, parent_id=self.parent_resource.id)
        else:
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
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
        levels = 0
        if hasattr(self.model, 'get_url_kwarg') and self.model.get_url_kwarg() in kwargs:
            levels += 1
        levels = levels + 1 if isinstance(self, ListModelMixin) or isinstance(self, CreateModelMixin) else levels + 2
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=levels)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_head_of(self.parent_resource)

    def get_queryset(self):
        if self.child_list_attribute is 'concepts':
            all_children = self.parent_resource_version.get_concept_ids()
        elif self.child_list_attribute is 'mappings':
            all_children = self.parent_resource_version.get_mapping_ids()
        else:
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
        if not self.versioned_object:
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
