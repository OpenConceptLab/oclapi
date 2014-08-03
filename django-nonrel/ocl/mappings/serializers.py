from rest_framework import serializers
from concepts.views import ConceptBaseView
from mappings.models import Mapping
from oclapi.fields import HyperlinkedRelatedField

__author__ = 'misternando'


class MappingSerializer(serializers.Serializer):
    map_type = serializers.CharField(required=True)
    to_concept = HyperlinkedRelatedField(view_name='concept-detail', queryset=ConceptBaseView.queryset, lookup_kwarg='concept', lookup_field='concept', required=False)
    to_source_url = serializers.URLField(required=False)
    to_concept_name = serializers.CharField(required=False)
    to_concept_code = serializers.CharField(required=False)

    class Meta:
        model = Mapping
        lookup_field = 'id'

    def restore_object(self, attrs, instance=None):
        mapping = instance if instance else Mapping()
        mapping.map_type = attrs.get('map_type', mapping.map_type)
        mapping.to_concept = attrs.get('to_concept', mapping.to_concept)
        mapping.to_source_url = attrs.get('to_source_url', mapping.to_source_url)
        mapping.to_concept_name = attrs.get('to_concept_name', mapping.to_concept_name)
        mapping.to_concept_code = attrs.get('to_concept_code', mapping.to_concept_code)
        return mapping

    def save_object(self, obj, **kwargs):
        errors = Mapping.persist_new(obj, **kwargs)
        self._errors.update(errors)
