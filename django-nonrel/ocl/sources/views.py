from rest_framework import mixins, generics, status
from rest_framework.response import Response
from orgs.models import Organization
from sources.models import Source
from sources.serializers import SourceCreateSerializer


class DoesNotExist(object):
    pass


class SourceListView(mixins.CreateModelMixin,
                     generics.GenericAPIView):
    model = Source

    def post(self, request, *args, **kwargs):
        self.serializer_class = SourceCreateSerializer
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        belongs_to_org = kwargs.pop('mnemonic', None)
        if belongs_to_org:
            try:
                belongs_to_org = Organization.objects.get(mnemonic=belongs_to_org)
            except DoesNotExist:
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

