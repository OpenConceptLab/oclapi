from rest_framework import generics, permissions
from models import ConceptClass, NameLocale, ConceptDataType
from serializers import ConceptClassListSerializer, NameLocaleListSerializer, ConceptDataTypeListSerializer

class SelectionAttributeBaseView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]


class ConceptClassView(SelectionAttributeBaseView):
    serializer_class = ConceptClassListSerializer
    queryset = ConceptClass.objects.filter()

class NameLocaleView(SelectionAttributeBaseView):
    serializer_class = NameLocaleListSerializer
    queryset = NameLocale.objects.filter()

class ConceptDataTypeView(SelectionAttributeBaseView):
    serializer_class = ConceptDataTypeListSerializer
    queryset = ConceptDataType.objects.filter()