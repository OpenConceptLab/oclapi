from rest_framework import serializers
from concepts.fields import ConceptReferenceField, SourceReferenceField
from concepts.models import Concept
from mappings.models import Mapping
from oclapi.fields import HyperlinkedRelatedField

__author__ = 'misternando'


class MappingBaseSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    id = serializers.CharField(read_only=True)
    external_id = serializers.CharField(required=False)
    from_concept_url = ConceptReferenceField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=True, source='from_concept')
    to_concept_url = ConceptReferenceField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=False, source='to_concept')
    to_source_url = SourceReferenceField(view_name='source-detail', queryset=Concept.objects.all(), lookup_kwarg='source', lookup_field='source', required=False, source='to_source')
    from_concept_code = serializers.CharField(read_only=True)
    from_source = HyperlinkedRelatedField(source='from_source', read_only=True, view_name='source-detail')
    from_source_name = serializers.CharField(read_only=True)
    from_source_owner = serializers.CharField(read_only=True)
    to_source_name = serializers.CharField(read_only=True)
    to_source_owner = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)

    def restore_object(self, attrs, instance=None):
        mapping = instance if instance else Mapping()
        mapping.map_type = attrs.get('map_type', mapping.map_type)
        mapping.from_concept = attrs.get('from_concept', mapping.to_concept)
        mapping.to_concept = attrs.get('to_concept', mapping.to_concept)
        mapping.to_source = attrs.get('to_source', mapping.to_source)
        mapping.to_concept_name = attrs.get('to_concept_name', mapping.to_concept_name)
        mapping.to_concept_code = attrs.get('to_concept_code', mapping.to_concept_code)
        mapping.external_id = attrs.get('external_id', mapping.external_id)
        return mapping

    class Meta:
        model = Mapping
        lookup_field = 'mnemonic'


class MappingCreateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=True)
    from_concept_url = ConceptReferenceField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=True, source='from_concept')
    to_concept_url = ConceptReferenceField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=False, source='to_concept')
    to_source_url = SourceReferenceField(view_name='source-detail', queryset=Concept.objects.all(), lookup_kwarg='source', lookup_field='source', required=False, source='to_source')
    to_concept_code = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Mapping.persist_new(obj, request_user, **kwargs)
        self._errors.update(errors)


class MappingRetrieveDestroySerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=False)
    from_source_url = serializers.URLField(required=False)
    to_source_url = serializers.URLField(required=False)
    to_concept_name = serializers.CharField(required=False, source='get_to_concept_name')
    to_concept_code = serializers.CharField(required=False, source='get_to_concept_code')


class MappingUpdateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False)
    to_concept_code = serializers.CharField(required=False)
    to_source_url = serializers.URLField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Mapping.persist_changes(obj, request_user)
        self._errors.update(errors)
