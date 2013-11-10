from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView, DestroyAPIView, ListAPIView
from rest_framework.response import Response
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptCreateSerializer, ConceptListSerializer, ConceptDetailSerializer
from oclapi.permissions import HasAccessToVersionedObject
from oclapi.views import SubResourceMixin, ResourceVersionMixin


class ConceptBaseView(SubResourceMixin):
    lookup_field = 'concept'
    pk_field = 'mnemonic'
    model = Concept
    queryset = Concept.objects.filter(is_active=True)
    permission_classes = (HasAccessToVersionedObject,)


class ConceptRetrieveUpdateDestroyView(ConceptBaseView, RetrieveAPIView):
    serializer_class = ConceptDetailSerializer


class ConceptListView(ListAPIView):
    model = Concept
    queryset = Concept.objects.filter(is_active=True)
    serializer_class = ConceptListSerializer


class ConceptCreateView(ConceptBaseView,
                        mixins.CreateModelMixin):

    def post(self, request, *args, **kwargs):
        self.serializer_class = ConceptCreateSerializer
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
                return Response(serializer.data, status=status.HTTP_201_CREATED,
                                headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class ConceptVersionBaseView(ResourceVersionMixin):
#     lookup_field = 'version'
#     pk_field = 'mnemonic'
#     model = ConceptVersion
#     queryset = ConceptVersion.objects.filter(is_active=True)
#     permission_classes = (HasAccessToVersionedObject,)
#
#
# class ConceptVersionListView(ConceptVersionBaseView,
#                              mixins.CreateModelMixin,
#                              mixins.ListModelMixin):
#
#     def get(self, request, *args, **kwargs):
#         self.serializer_class = ConceptVersionListSerializer
#         return self.list(request, *args, **kwargs)
#
#     def post(self, request, *args, **kwargs):
#         self.serializer_class = ConceptVersionCreateSerializer
#         return self.create(request, *args, **kwargs)
#
#     def create(self, request, *args, **kwargs):
#         if not self.versioned_object:
#             return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         serializer = self.get_serializer(data=request.DATA, files=request.FILES)
#         if serializer.is_valid():
#             self.pre_save(serializer.object)
#             self.object = serializer.save(force_insert=True, versioned_object=self.versioned_object)
#             if serializer.is_valid():
#                 self.post_save(self.object, created=True)
#                 headers = self.get_success_headers(serializer.data)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED,
#                                 headers=headers)
#
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


