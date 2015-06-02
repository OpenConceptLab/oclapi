from rest_framework import serializers
from concepts.fields import ConceptURLField, SourceURLField
from concepts.models import Concept
from mappings.models import Mapping

__author__ = 'misternando'


class MappingBaseSerializer(serializers.Serializer):

    def restore_object(self, attrs, instance=None):
        mapping = instance if instance else Mapping()
        mapping.map_type = attrs.get('map_type', mapping.map_type)
        from_concept = None
        try:
            from_concept = mapping.from_concept
        except Concept.DoesNotExist: pass
        mapping.retired = attrs.get('retired', mapping.retired)
        mapping.from_concept = attrs.get('from_concept', from_concept)
        mapping.to_concept = attrs.get('to_concept', mapping.to_concept)
        mapping.to_source = attrs.get('to_source', mapping.to_source)
        mapping.to_concept_name = attrs.get('to_concept_name', mapping.to_concept_name)
        mapping.to_concept_code = attrs.get('to_concept_code', mapping.to_concept_code)
        mapping.external_id = attrs.get('external_id', mapping.external_id)
        return mapping

    class Meta:
        model = Mapping
        lookup_field = 'mnemonic'


class MappingDetailSerializer(MappingBaseSerializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    id = serializers.CharField(read_only=True)
    external_id = serializers.CharField(required=False)
    retired = serializers.BooleanField(required=False)
    map_type = serializers.CharField(required=True)

    from_source_owner = serializers.CharField(read_only=True)
    from_source_owner_type = serializers.CharField(read_only=True)
    from_source_name = serializers.CharField(read_only=True)
    from_source_url = serializers.URLField(read_only=True)
    from_concept_code = serializers.CharField(read_only=True)
    from_concept_name = serializers.CharField(read_only=True)
    from_concept_url = serializers.URLField()

    to_source_owner = serializers.CharField(read_only=True)
    to_source_owner_type = serializers.CharField(read_only=True)
    to_source_name = serializers.CharField(read_only=True)
    to_source_url = serializers.URLField()
    to_concept_code = serializers.CharField(source='get_to_concept_code')
    to_concept_name = serializers.CharField(source='get_to_concept_name')
    to_concept_url = serializers.URLField()

    source = serializers.CharField(read_only=True)
    owner = serializers.CharField(read_only=True)
    owner_type = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)

    extras = serializers.WritableField(required=False)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)


class MappingListSerializer(MappingBaseSerializer):
    external_id = serializers.CharField(required=False)
    retired = serializers.BooleanField(required=False)
    map_type = serializers.CharField(required=True)
    source = serializers.CharField(read_only=True)
    owner = serializers.CharField(read_only=True)
    owner_type = serializers.CharField(read_only=True)
    from_concept_url = serializers.URLField(read_only=True)
    to_concept_url = serializers.URLField()
    to_source_url = serializers.URLField()
    to_concept_code = serializers.CharField(source='get_to_concept_code')
    to_concept_name = serializers.CharField(source='get_to_concept_name')
    url = serializers.CharField(read_only=True)


class MappingCreateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=True)
    from_concept_url = ConceptURLField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=True, source='from_concept')
    to_concept_url = ConceptURLField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=False, source='to_concept')
    to_source_url = SourceURLField(view_name='source-detail', queryset=Concept.objects.all(), lookup_kwarg='source', lookup_field='source', required=False, source='to_source')
    to_concept_code = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False)
    external_id = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Mapping.persist_new(obj, request_user, **kwargs)
        self._errors.update(errors)


class MappingUpdateSerializer(MappingBaseSerializer):
    map_type = serializers.CharField(required=False)
    retired = serializers.BooleanField(required=False)
    from_concept_url = ConceptURLField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=False, source='from_concept')
    to_concept_url = ConceptURLField(view_name='concept-detail', queryset=Concept.objects.all(), lookup_kwarg='concept', lookup_field='concept', required=False, source='to_concept')
    to_source_url = SourceURLField(view_name='source-detail', queryset=Concept.objects.all(), lookup_kwarg='source', lookup_field='source', required=False, source='to_source')
    to_concept_code = serializers.CharField(required=False)
    to_concept_name = serializers.CharField(required=False)
    external_id = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Mapping.persist_changes(obj, request_user)
        self._errors.update(errors)
