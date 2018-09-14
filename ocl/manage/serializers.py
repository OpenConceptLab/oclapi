from rest_framework import serializers

class ReferenceSerializer(serializers.Serializer):
    source_type = serializers.CharField(source='reference_definition.source_type.__name__', read_only=True)
    source_field = serializers.CharField(source='reference_definition.source_field', read_only=True)
    target_type = serializers.CharField(source='reference_definition.target_type.__name__', read_only=True)
    target_field = serializers.CharField(source='reference_definition.target_field', read_only=True)
    use_object_id = serializers.BooleanField(source='reference_definition.use_object_id', read_only=True)

    source_id = serializers.CharField(read_only=True)
    broken_reference = serializers.CharField(read_only=True)

class ReferenceListSerializer(serializers.Serializer):
    broken_total_count = serializers.IntegerField(read_only=True)
    broken_counts = serializers.SerializerMethodField(method_name='get_broken_counts')
    candidate_counts = serializers.SerializerMethodField(method_name='get_candidate_counts')
    broken_references = ReferenceSerializer()

    def get_broken_counts(self, obj):
        return obj.broken_counts

    def get_candidate_counts(self, obj):
        return obj.candidate_counts


