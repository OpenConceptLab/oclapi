from django.core.validators import RegexValidator
from rest_framework import serializers
from collection.fields import ConceptReferenceField
from concepts.fields import LocalizedTextListField
from concepts.models import Concept, ConceptVersion, ConceptReference
from oclapi.fields import HyperlinkedRelatedField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import ResourceVersionSerializer
from sources.models import Source


class ConceptListSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    url = serializers.URLField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()

    class Meta:
        model = Concept


class ConceptDetailSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()
    url = serializers.URLField()
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField(name_override='description')
    extras = serializers.WritableField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    extras = serializers.WritableField()

    class Meta:
        model = Concept


class ConceptCreateSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    concept_class = serializers.CharField()
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False, name_override='description')
    extras = serializers.WritableField(required=False)

    class Meta:
        model = Concept
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        concept = instance if instance else Concept()
        concept.mnemonic = attrs.get(self.Meta.lookup_field, concept.mnemonic)
        concept.concept_class = attrs.get('concept_class', concept.concept_class)
        concept.datatype = attrs.get('datatype', concept.datatype)
        concept.extras = attrs.get('extras', concept.extras)
        concept.names = attrs.get('names', concept.names)  # Is this desired behavior??
        concept.descriptions = attrs.get('descriptions', concept.descriptions)  # Is this desired behavior??
        concept.extras = attrs.get('extras', concept.extras)
        return concept

    def save_object(self, obj, **kwargs):
        errors = Concept.persist_new(obj, **kwargs)
        self._errors.update(errors)


class ConceptVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='name')
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()
    version = serializers.CharField(source='mnemonic')
    extras = serializers.WritableField()

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'
        versioned_object_view_name = 'concept-detail'


class ConceptVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(source='versioned_object_type')
    uuid = serializers.CharField(source='id')
    id = serializers.CharField(source='name')
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField(name_override='description')
    extras = serializers.WritableField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    source_url = HyperlinkedRelatedField(source='source', view_name='source-detail', queryset=Source.objects.all())
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    mappings_url = serializers.URLField()
    version = serializers.CharField(source='mnemonic')
    extras = serializers.WritableField()

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'
        versioned_object_view_name = 'concept-detail'


class ConceptVersionUpdateSerializer(serializers.Serializer):
    concept_class = serializers.CharField(required=True)
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False, name_override='description')
    extras = serializers.WritableField(required=False)

    class Meta:
        model = ConceptVersion

    def restore_object(self, attrs, instance=None):
        instance.concept_class = attrs.get('concept_class', instance.concept_class)
        instance.datatype = attrs.get('datatype', instance.datatype)
        instance.extras = attrs.get('extras', instance.extras)
        instance.names = attrs.get('names', instance.names)  # Is this desired behavior??
        instance.descriptions = attrs.get('descriptions', instance.descriptions)  # Is this desired behavior??
        return instance

    def save_object(self, obj, **kwargs):
        errors = ConceptVersion.persist_clone(obj, **kwargs)
        self._errors.update(errors)


class ConceptReferenceCreateSerializer(serializers.Serializer):
    url = ConceptReferenceField(source='concept', required=True, view_name='conceptversion-detail', lookup_kwarg='concept_version', queryset=ConceptVersion.objects.all())
    id = serializers.CharField(source='mnemonic', required=False)
    extras = serializers.WritableField(read_only=False)

    class Meta:
        model = ConceptReference
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        concept_reference = instance if instance else ConceptReference()
        concept_reference.extras = attrs.get('extras', concept_reference.extras)
        concept = attrs.get('concept', None)
        if concept:
            concept_reference.concept = concept
            if hasattr(concept, '_concept_version'):
                concept_reference.concept_version = concept._concept_version
            elif hasattr(concept, '_source_version'):
                concept_reference.source_version = concept._source_version
        concept_reference.mnemonic = attrs.get(self.Meta.lookup_field, concept_reference.mnemonic)
        if not concept_reference.mnemonic:
            concept_reference.mnemonic = "%s..%s" % (concept_reference.concept.parent, concept_reference.concept)
        return concept_reference

    def save_object(self, obj, **kwargs):
        errors = ConceptReference.persist_new(obj, **kwargs)
        self._errors.update(errors)


class ConceptReferenceDetailSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    concept_reference_url = serializers.URLField(read_only=True)
    concept_class = serializers.CharField(read_only=True)
    data_type = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    owner = serializers.CharField(read_only=True, source='owner_name')
    owner_type = serializers.CharField(read_only=True)
    owner_url = serializers.URLField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    display_locale = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True, source='concept_version')
    is_current_version = serializers.BooleanField(read_only=True)
    extras = serializers.WritableField(required=False)

    class Meta:
        model = ConceptReference
        lookup_field = 'mnemonic'