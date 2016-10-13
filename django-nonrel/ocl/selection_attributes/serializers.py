from rest_framework import serializers
from models import ConceptClass, NameLocale, ConceptDataType


class SelectionAttributeBaseSerializer(serializers.Serializer):
    name = serializers.CharField()


class ConceptClassListSerializer(SelectionAttributeBaseSerializer):
    class Meta:
        model = ConceptClass

class NameLocaleListSerializer(SelectionAttributeBaseSerializer):
    code = serializers.CharField()

    class Meta:
        model = NameLocale

class ConceptDataTypeListSerializer(SelectionAttributeBaseSerializer):
    class Meta:
        model = ConceptDataType
