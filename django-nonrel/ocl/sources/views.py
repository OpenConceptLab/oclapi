from rest_framework import mixins, generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from oclapi.views import SubresourceMixin
from orgs.models import Organization
from sources.models import Source
from sources.serializers import SourceCreateSerializer, SourceListSerializer, SourceDetailSerializer


class SourceBaseView(SubresourceMixin):
    url_param = 'source'

    def get_queryset(self):
        queryset = super(SourceBaseView, self).get_queryset()
        if self.parent_resource:
            queryset = queryset.filter(mnemonic__in=self.parent_resource.sources)
        return queryset


class SourceDetailView(mixins.RetrieveModelMixin,
                       SourceBaseView):
    serializer_class = SourceDetailSerializer
    queryset = Source.objects.filter(is_active=True)
    lookup_field = 'mnemonic'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Determine the base queryset to use.
        if queryset is None:
            queryset = self.filter_queryset(self.get_queryset())
        else:
            pass  # Deprecation warning

        # Perform the lookup filtering.
        lookup = self.kwargs.get(self.url_param, None)
        filter_kwargs = {self.lookup_field: lookup}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class SourceListView(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     SourceBaseView):
    model = Source
    queryset = Source.objects.filter(is_active=True)

    def get_serializer_context(self):
        context = {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
        context.update(self.additional_serializer_context)
        return context

    def get(self, request, *args, **kwargs):
        self.serializer_class = SourceListSerializer
        if self.user_is_self:
            self.additional_serializer_context.update({
                'related_view_name': 'user-source-detail',
                'url_param': 'mnemonic',
            })
        elif self.parent_resource:
            self.additional_serializer_context.update({
                'related_view_name': '%s-source-detail' % self.parent_resource_type.__name__.lower(),
                'url_param': self.url_param,
                'related_url_param': self.parent_resource_kwarg,
                'related_url_param_value': self.parent_resource_lookup
            })

        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.serializer_class = SourceCreateSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        belongs_to_org = kwargs.pop('mnemonic', None)
        if belongs_to_org:
            try:
                belongs_to_org = Organization.objects.get(mnemonic=belongs_to_org)
            except:
                return Response(['Organization: %s does not exist.' % belongs_to_org], status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True, owner=request.user, belongs_to_org=belongs_to_org)
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

