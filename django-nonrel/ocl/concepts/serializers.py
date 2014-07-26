from django.core.validators import RegexValidator
from rest_framework import serializers
from concepts.fields import LocalizedTextListField
from concepts.models import Concept, ConceptVersion
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import ResourceVersionSerializer


class ConceptListSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    conceptClass = serializers.CharField(source='concept_class')
    datatype = serializers.CharField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    ownerType = serializers.CharField(source='owner_type')
    displayName = serializers.CharField(source='display_name')
    displayLocale = serializers.CharField(source='display_locale')
    url = serializers.CharField()
    ownerUrl = serializers.CharField(source='owner_url')

    class Meta:
        model = Concept


class ConceptDetailSerializer(serializers.Serializer):
    conceptClass = serializers.CharField(source='concept_class')
    datatype = serializers.CharField()
    displayName = serializers.CharField(source='display_name')
    displayLocale = serializers.CharField(source='display_locale')
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    url = serializers.CharField()
    ownerUrl = serializers.CharField(source='owner_url')

    class Meta:
        model = Concept


class ConceptCreateSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    conceptClass = serializers.CharField(required=True, source='concept_class')
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False)

    class Meta:
        model = Concept
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        concept = instance if instance else Concept()
        concept.mnemonic = attrs.get(self.Meta.lookup_field, concept.mnemonic)
        concept.concept_class = attrs.get('concept_class', concept.concept_class)
        concept.datatype = attrs.get('datatype', concept.datatype)
        concept.names = attrs.get('names', concept.names)  # Is this desired behavior??
        concept.descriptions = attrs.get('descriptions', concept.descriptions)  # Is this desired behavior??
        return concept

    def save_object(self, obj, **kwargs):
        errors = Concept.persist_new(obj, **kwargs)
        self._errors.update(errors)


class ConceptVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='name')
    conceptClass = serializers.CharField(source='concept_class')
    datatype = serializers.CharField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    ownerType = serializers.CharField(source='owner_type')
    displayName = serializers.CharField(source='display_name')
    displayLocale = serializers.CharField(source='display_locale')
    version = serializers.CharField(source='mnemonic')

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'
        versioned_object_view_name = 'concept-detail'
        fields = ('id', 'conceptClass', 'datatype', 'retired', 'source', 'owner', 'ownerType', 'displayName', 'displayLocale', 'url', 'versionUrl', 'version')


class ConceptVersionDetailSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='name')
    conceptClass = serializers.CharField(source='concept_class')
    datatype = serializers.CharField()
    displayName = serializers.CharField(source='display_name')
    displayLocale = serializers.CharField(source='display_locale')
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    version = serializers.CharField(source='mnemonic')

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'


class ConceptVersionUpdateSerializer(serializers.Serializer):
    conceptClass = serializers.CharField(required=True, source='concept_class')
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False)

    class Meta:
        model = ConceptVersion

    def restore_object(self, attrs, instance=None):
        instance.concept_class = attrs.get('concept_class', instance.concept_class)
        instance.datatype = attrs.get('datatype', instance.datatype)
        instance.names = attrs.get('names', instance.names)  # Is this desired behavior??
        instance.descriptions = attrs.get('descriptions', instance.descriptions)  # Is this desired behavior??
        return instance

    def save_object(self, obj, **kwargs):
        errors = ConceptVersion.persist_clone(obj, **kwargs)
        self._errors.update(errors)

