from rest_framework import serializers
from concepts.views import ConceptBaseView
from mappings.models import Mapping
from oclapi.fields import HyperlinkedRelatedField

__author__ = 'misternando'


class MappingBaseSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    id = serializers.CharField(read_only=True)
    from_concept = HyperlinkedRelatedField(source='parent', read_only=True, view_name='concept-detail')
    from_concept_code = serializers.CharField(read_only=True)
    from_source = HyperlinkedRelatedField(source='from_source', read_only=True, view_name='source-detail')
    from_source_name = serializers.CharField(read_only=True)
    from_source_owner = serializers.CharField(read_only=True)
    to_concept = HyperlinkedRelatedField(view_name='concept-detail', queryset=ConceptBaseView.queryset, lookup_kwarg='concept', lookup_field='concept', required=False)
    to_source_name = serializers.CharField(read_only=True)
    to_source_owner = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def restore_object(self, attrs, instance=None):
        mapping = instance if instance else Mapping()
        mapping.map_type = attrs.get('map_type', mapping.map_type)
        mapping.to_concept = attrs.get('to_concept', mapping.to_concept)
        mapping.to_source_url = attrs.get('to_source_url', mapping.to_source_url)
        mapping.to_concept_name = attrs.get('to_concept_name', mapping.to_concept_name)
        mapping.to_concept_code = attrs.get('to_concept_code', mapping.to_concept_code)
        return mapping

    class Meta:
        model = Mapping
        lookup_field = 'mnemonic'


class MappingCreateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=True)
    to_concept_name = serializers.CharField(required=False)
    to_concept_code = serializers.CharField(required=False)
    to_source_url = serializers.URLField(required=False)

    def save_object(self, obj, **kwargs):
        errors = Mapping.persist_new(obj, **kwargs)
        self._errors.update(errors)


class MappingRetrieveDestroySerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False, source='get_to_concept_name')
    to_concept_code = serializers.CharField(required=False, source='get_to_concept_code')
    to_source_url = serializers.URLField(required=False, source='get_to_source_url')


class MappingUpdateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False)
    to_concept_code = serializers.CharField(required=False)
    to_source_url = serializers.URLField(required=False)

    def save_object(self, obj, **kwargs):
        errors = Mapping.persist_changes(obj)
        self._errors.update(errors)
