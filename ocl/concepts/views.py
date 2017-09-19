from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.query import EmptyQuerySet
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, status
from rest_framework.generics import (RetrieveAPIView, get_object_or_404, UpdateAPIView,
                                     DestroyAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView,
                                     ListCreateAPIView, ListAPIView)
from rest_framework.response import Response
from concepts.filters import LimitSourceVersionFilter, PublicConceptsSearchFilter, LimitCollectionVersionFilter
from concepts.models import Concept, ConceptVersion, LocalizedText
from concepts.permissions import CanViewParentDictionary, CanEditParentDictionary
from concepts.serializers import (ConceptDetailSerializer, ConceptVersionListSerializer,
                                  ConceptVersionDetailSerializer, ConceptVersionUpdateSerializer,
                                  ConceptVersionsSerializer, ConceptNameSerializer,
                                  ConceptDescriptionSerializer)
from mappings.models import Mapping
from mappings.serializers import MappingListSerializer
from oclapi.filters import HaystackSearchFilter
from oclapi.mixins import ListWithHeadersMixin, ConceptVersionCSVFormatterMixin
from oclapi.models import ACCESS_TYPE_NONE, ResourceVersionModel
from oclapi.views import (ConceptDictionaryMixin, VersionedResourceChildMixin, BaseAPIView,
                          ChildResourceMixin, parse_updated_since_param, ResourceVersionMixin)
from sources.models import SourceVersion
from orgs.models import Organization
from users.models import UserProfile


INCLUDE_RETIRED_PARAM = 'includeRetired'
INCLUDE_MAPPINGS_PARAM = 'includeMappings'
INCLUDE_INVERSE_MAPPINGS_PARAM = 'includeInverseMappings'
LIMIT_PARAM = 'limit'


class ConceptBaseView(ChildResourceMixin):
    lookup_field = 'concept'
    pk_field = 'mnemonic'
    model = Concept
    permission_classes = (CanViewParentDictionary,)
    child_list_attribute = 'concepts'


class ConceptRetrieveUpdateDestroyView(ConceptBaseView, RetrieveAPIView,
                                       UpdateAPIView, DestroyAPIView):
    serializer_class = ConceptDetailSerializer

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.kwargs = kwargs
            self.request = self.initialize_request(request, *args, **kwargs)
            self.initial(self.request, *args, **kwargs)
            concept = self.get_object()
            kwargs.update({'versioned_object': concept})
            delegate_view = ConceptVersionRetrieveView.as_view()
            rtn = delegate_view(request, *args, **kwargs)
            return rtn
        return super(ConceptRetrieveUpdateDestroyView, self).dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        if hasattr(self.parent_resource, 'versioned_object'):
            parent_versioned_object = self.parent_resource.versioned_object
            if self.parent_resource != type(self.parent_resource).get_latest_version_of(parent_versioned_object):
                return Response({'non_field_errors': 'Parent version is not the latest.  Cannot update concept.'}, status=status.HTTP_400_BAD_REQUEST)

        self.serializer_class = ConceptVersionUpdateSerializer
        partial = kwargs.pop('partial', True)
        self.object = self.get_object_or_none()

        if self.object is None:
            return Response({'non_field_errors': 'Could not find concept to update'}, status=status.HTTP_404_NOT_FOUND)
        else:
            latest_version = ConceptVersion.get_latest_version_of(self.object)
            self.object = latest_version.clone()
            save_kwargs = {'force_update': False}
            success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if serializer.is_valid():
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                serializer = ConceptVersionDetailSerializer(self.object, context={'request': request})
                return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        concept = self.get_object_or_none()
        if concept is None:
            return Response(
                {'non_field_errors': 'Could not find concept to retire'},
                status=status.HTTP_404_NOT_FOUND)
        update_comment = None
        if 'update_comment' in request.DATA :
            update_comment = request.DATA.get('update_comment')

        errors = Concept.retire(concept, request.user, update_comment=update_comment)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConceptVersionListAllView(BaseAPIView, ConceptVersionCSVFormatterMixin, ListWithHeadersMixin):
    model = ConceptVersion
    permission_classes = (CanViewParentDictionary,)
    filter_backends = [PublicConceptsSearchFilter]
    queryset = ConceptVersion.objects.filter(is_active=True)
    solr_fields = {
        'name': {'sortable': True, 'filterable': False},
        'lastUpdate': {'sortable': True, 'filterable': False},
        'is_latest_version': {'sortable': False, 'filterable': True},
        'conceptClass': {'sortable': False, 'filterable': True, 'facet': True},
        'datatype': {'sortable': False, 'filterable': True, 'facet': True},
        'locale': {'sortable': False, 'filterable': True, 'facet': True},
        'retired': {'sortable': False, 'filterable': True, 'facet': True},
        'source': {'sortable': False, 'filterable': True, 'facet': True},
        'collection': {'sortable': False, 'filterable': True, 'facet': True},
        'owner': {'sortable': False, 'filterable': True, 'facet': True},
        'ownerType': {'sortable': False, 'filterable': True, 'facet': True},
    }
    updated_since = None
    include_retired = False
    default_filters = {'is_active':True, 'is_latest_version': True}

    def get_serializer_context(self):
        context = {'request': self.request}
        if self.is_verbose(self.request):
            context.update({'verbose': True})
        if self.request.GET.get(INCLUDE_INVERSE_MAPPINGS_PARAM):
            context.update({'include_indirect_mappings': True})
        if self.request.GET.get(INCLUDE_MAPPINGS_PARAM):
            context.update({'include_direct_mappings': True})
        return context

    def get(self, request, *args, **kwargs):
        self.updated_since = parse_updated_since_param(request)
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer
        self.limit = 100 if request.QUERY_PARAMS.get('csv') else request.QUERY_PARAMS.get(LIMIT_PARAM, 25)
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(ConceptVersionListAllView, self).get_queryset()
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        queryset = queryset.filter(**self.default_filters)
        if not self.request.user.is_staff:
            queryset = queryset.filter(~Q(public_access=ACCESS_TYPE_NONE))
        return queryset[0:self.limit]


class ConceptCreateView(ConceptBaseView,
                        mixins.CreateModelMixin):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            delegate_view = ConceptVersionListView.as_view()
            return delegate_view(request, *args, **kwargs)
        return super(ConceptCreateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.permission_classes = (CanEditParentDictionary,)
        self.serializer_class = ConceptDetailSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            save_kwargs = {
                'force_insert': True,
                'parent_resource': self.parent_resource,
                'child_list_attribute': self.child_list_attribute
            }
            self.object = serializer.save(**save_kwargs)
            if serializer.is_valid():
                self.post_save(self.object, created=True)
                headers = self.get_success_headers(serializer.data)
                latest_version = ConceptVersion.get_latest_version_of(self.object)
                serializer = ConceptVersionDetailSerializer(latest_version)
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConceptVersionsView(ConceptDictionaryMixin, ListWithHeadersMixin):
    serializer_class = ConceptVersionListSerializer
    permission_classes = (CanViewParentDictionary,)

    def get(self, request, *args, **kwargs):
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionsSerializer
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ConceptVersion.objects.filter(versioned_object_id=self.parent_resource.id,
                                             is_active=True)


class ConceptVersionMixin():
    lookup_field = 'concept_version'
    pk_field = 'mnemonic'
    model = ConceptVersion
    parent_resource_version_model = SourceVersion
    permission_classes = (CanViewParentDictionary,)
    child_list_attribute = 'concepts'


class ConceptVersionListView(ConceptVersionMixin, VersionedResourceChildMixin,
                             ConceptVersionCSVFormatterMixin, ListWithHeadersMixin):
    serializer_class = ConceptVersionListSerializer
    permission_classes = (CanViewParentDictionary,)
    solr_fields = {
        'name': {'sortable': True, 'filterable': False},
        'lastUpdate': {'sortable': True, 'filterable': False},
        'is_latest_version': {'sortable': False, 'filterable': True},
        'conceptClass': {'sortable': False, 'filterable': True, 'facet': True},
        'datatype': {'sortable': False, 'filterable': True, 'facet': True},
        'locale': {'sortable': False, 'filterable': True, 'facet': True},
        'retired': {'sortable': False, 'filterable': True, 'facet': True},
        'source': {'sortable': False, 'filterable': True, 'facet': True},
        'collection': {'sortable': False, 'filterable': True, 'facet': True},
        'owner': {'sortable': False, 'filterable': True, 'facet': True},
        'ownerType': {'sortable': False, 'filterable': True, 'facet': True},
    }
    updated_since = None
    include_retired = False

    def get_serializer_context(self):
        context = {'request': self.request}
        if self.request.GET.get('verbose'):
            context.update({'verbose': True})
        if 'version' not in self.kwargs and 'concept_version' not in self.kwargs:
            if self.request.GET.get('include_indirect_mappings'):
                context.update({'include_indirect_mappings': True})
            if self.request.GET.get('include_direct_mappings'):
                context.update({'include_direct_mappings': True})
        return context

    def get(self, request, *args, **kwargs):
        self.filter_backends = [LimitCollectionVersionFilter] if 'collection' in kwargs else [LimitSourceVersionFilter]
        self.updated_since = parse_updated_since_param(request)
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        self.serializer_class = ConceptVersionDetailSerializer if self.is_verbose(request) else ConceptVersionListSerializer

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        if ('collection' in self.kwargs and 'version' not in self.kwargs) or ('collection' in self.kwargs and 'version' in self.kwargs and self.kwargs['version'] == 'HEAD'):
            all_children = getattr(self.parent_resource_version, self.child_list_attribute) or []
            queryset = super(ConceptDictionaryMixin, self).get_queryset()
            queryset = queryset.filter(versioned_object_id__in=all_children, is_latest_version=True)
        else:
            queryset = super(ConceptVersionListView, self).get_queryset()

        queryset = queryset.filter(is_active=True)
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        if self.updated_since:
            queryset = queryset.filter(updated_at__gte=self.updated_since)
        return queryset

    def get_owner(self):
        owner = None
        if 'user' in self.kwargs:
            owner_id = self.kwargs['user']
            owner = UserProfile.objects.get(mnemonic=owner_id)
        elif 'org' in self.kwargs:
            owner_id = self.kwargs['org']
            owner = Organization.objects.get(mnemonic=owner_id)
        return owner


class ConceptVersionRetrieveView(ConceptVersionMixin, ResourceVersionMixin, RetrieveAPIView):
    lookup_field = 'concept_version'
    serializer_class = ConceptVersionDetailSerializer
    permission_classes = (CanViewParentDictionary,)
    versioned_object = None

    def initialize(self, request, path_info_segment, **kwargs):
        self.versioned_object = kwargs.pop('versioned_object', None)
        super(ConceptVersionRetrieveView, self).initialize(request, path_info_segment, **kwargs)

    def get_serializer_context(self):
        context = {'request': self.request}
        if self.request.GET.get('verbose'):
            context.update({'verbose': True})
        if self.request.GET.get(INCLUDE_INVERSE_MAPPINGS_PARAM):
            context.update({'include_indirect_mappings': True})
        if self.request.GET.get(INCLUDE_MAPPINGS_PARAM):
            context.update({'include_direct_mappings': True})
        return context

    def get_object(self, queryset=None):
        if self.versioned_object:
            concept_version_identifier = self.kwargs.get(self.lookup_field)
            if not concept_version_identifier:
                concept = self.versioned_object
                conceptVersion = ConceptVersion.get_latest_version_of(concept)
                return conceptVersion
            queryset = self.get_queryset()
            filter_kwargs = {'versioned_object_id': self.versioned_object.id,
                             self.pk_field: concept_version_identifier}
            return get_object_or_404(queryset, **filter_kwargs)
        return super(ConceptVersionRetrieveView, self).get_object()


class ConceptMappingsView(ConceptBaseView, ListAPIView):
    serializer_class = MappingListSerializer
    filter_backends = [HaystackSearchFilter, ]
    queryset = Mapping.objects.filter(is_active=True)
    concept = None
    include_inverse_mappings = False
    include_retired = False
    parent_resource_version = None
    updated_since = None
    solr_fields = {}

    def initialize(self, request, path_info_segment, **kwargs):
        self.include_retired = request.QUERY_PARAMS.get(INCLUDE_RETIRED_PARAM, False)
        include_inverse_param = request.GET.get(INCLUDE_INVERSE_MAPPINGS_PARAM, 'false')
        self.include_inverse_mappings = 'true' == include_inverse_param
        parent_path_info = self.get_parent_in_path(path_info_segment, levels=1)
        if parent_path_info and '/' != parent_path_info:
            self.concept = self.get_object_for_path(parent_path_info, self.request)
            parent_path_info = self.get_parent_in_path(parent_path_info, levels=2)
            if parent_path_info and '/' != parent_path_info:
                self.parent_resource = self.get_object_for_path(parent_path_info, self.request)
                if hasattr(self.parent_resource, 'versioned_object'):
                    self.parent_resource_version = self.parent_resource
                    self.parent_resource = self.parent_resource.versioned_object
                else:
                    self.parent_resource_version = SourceVersion.get_latest_version_of(self.parent_resource)

    def get_queryset(self):
        if not self.parent_resource:
            # pathological case
            return EmptyQuerySet()
        queryset = super(ChildResourceMixin, self).get_queryset()
        queryset = queryset.filter(parent_id=self.parent_resource.id)
        if self.include_inverse_mappings:
            queryset = queryset.filter(Q(from_concept=self.concept) | Q(to_concept=self.concept))
        else:
            queryset = queryset.filter(from_concept=self.concept)
        if not self.include_retired:
            queryset = queryset.filter(~Q(retired=True))
        return queryset


class ConceptExtrasView(ConceptBaseView, ListAPIView):
    permission_classes = (CanViewParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=1)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)

    def list(self, request, *args, **kwargs):
        extras = self.parent_resource_version.extras or {}
        return Response(extras)


class ConceptExtraRetrieveUpdateDestroyView(ConceptBaseView, VersionedResourceChildMixin,
                                            RetrieveUpdateDestroyAPIView):
    permission_classes = (CanEditParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewParentDictionary,)
        self.parent_path_info = self.get_parent_in_path(path_info_segment, levels=2)
        self.parent_resource = None
        if self.parent_path_info and '/' != self.parent_path_info:
            self.parent_resource = self.get_object_for_path(self.parent_path_info, self.request)
        if hasattr(self.parent_resource, 'versioned_object'):
            self.parent_resource_version = self.parent_resource
            self.parent_resource = self.parent_resource_version.versioned_object
        else:
            self.parent_resource_version = ResourceVersionModel.get_latest_version_of(self.parent_resource)
        self.key = kwargs.get('extra')
        self.parent_resource_version = self.parent_resource_version.clone()
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
            return Response(
                ['Must specify %s param in body.' % self.key],
                status=status.HTTP_400_BAD_REQUEST)

        self.extras[self.key] = value
        self.parent_resource_version.update_comment = 'Updated extras: %s=%s.' % (self.key, value)
        errors = ConceptVersion.persist_clone(self.parent_resource_version, request.user)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({self.key: self.extras[self.key]})

    def delete(self, request, *args, **kwargs):
        if self.key in self.extras:
            del self.extras[self.key]
            self.parent_resource_version.update_comment = 'Deleted extra %s.' % self.key
            errors = ConceptVersion.persist_clone(self.parent_resource_version, request.user)
            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Not found."}, status.HTTP_404_NOT_FOUND)


class ConceptLabelListCreateView(ConceptBaseView, VersionedResourceChildMixin,
                                 ListWithHeadersMixin, ListCreateAPIView):
    model = LocalizedText
    parent_list_attribute = None
    permission_classes = (CanEditParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewParentDictionary,)
        super(ConceptLabelListCreateView, self).initialize(request, path_info_segment, **kwargs)

    def get_queryset(self):
        return getattr(self.parent_resource_version, self.parent_list_attribute)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            new_version = self.parent_resource_version.clone()
            labels = getattr(new_version, self.parent_list_attribute)
            labels.append(serializer.object)
            new_version.update_comment = 'Added to %s: %s.' % (self.parent_list_attribute,
                                                               serializer.object.name)
            errors = ConceptVersion.persist_clone(new_version, request.user)
            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConceptNameListCreateView(ConceptLabelListCreateView):
    serializer_class = ConceptNameSerializer
    parent_list_attribute = 'names'


class ConceptDescriptionListCreateView(ConceptLabelListCreateView):
    serializer_class = ConceptDescriptionSerializer
    parent_list_attribute = 'descriptions'


class ConceptLabelRetrieveUpdateDestroyView(ConceptBaseView, VersionedResourceChildMixin,
                                            RetrieveUpdateDestroyAPIView):
    model = LocalizedText
    parent_list_attribute = None
    permission_classes = (CanEditParentDictionary,)

    def initialize(self, request, path_info_segment, **kwargs):
        if request.method in ['GET', 'HEAD']:
            self.permission_classes = (CanViewParentDictionary,)
        super(ConceptLabelRetrieveUpdateDestroyView, self).initialize(request,
                                                                      path_info_segment,
                                                                      **kwargs)

    def get_object(self, queryset=None):
        uuid = self.kwargs.get('uuid')
        self.parent_resource_version = self.parent_resource_version.clone()
        labels = getattr(self.parent_resource_version, self.parent_list_attribute)
        for label in labels:
            if uuid == unicode(label.uuid):
                return label
        raise Http404()

    def update(self, request, *args, **kwargs):
        partial = True
        self.object = self.get_object()
        success_status_code = status.HTTP_200_OK

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if serializer.is_valid():
            self.parent_resource_version.update_comment = 'Updated %s in %s.' % (self.object.name, self.parent_list_attribute)
            errors = ConceptVersion.persist_clone(self.parent_resource_version, request.user)
            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=success_status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        index_to_remove = -1
        labels = getattr(self.parent_resource_version, self.parent_list_attribute)
        for i, label in enumerate(labels):
            if label.uuid == obj.uuid:
                index_to_remove = i
                break
        if index_to_remove >= 0:
            del labels[index_to_remove]
            self.parent_resource_version.update_comment = 'Deleted %s from %s.' % (obj.name, self.parent_list_attribute)
            errors = ConceptVersion.persist_clone(self.parent_resource_version, request.user)
            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConceptNameRetrieveUpdateDestroyView(ConceptLabelRetrieveUpdateDestroyView):
    parent_list_attribute = 'names'
    serializer_class = ConceptNameSerializer


class ConceptDescriptionRetrieveUpdateDestroyView(ConceptLabelRetrieveUpdateDestroyView):
    parent_list_attribute = 'descriptions'
    serializer_class = ConceptDescriptionSerializer

