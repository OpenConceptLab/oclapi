from rest_framework import serializers

class ReferenceSerializer(serializers.Serializer):
    source_id = serializers.CharField(read_only=True)
    target_id = serializers.CharField(read_only=True)
    deletable = serializers.BooleanField(read_only=True)
    deleted = serializers.BooleanField(read_only=True)
    item = serializers.SerializerMethodField('get_item')
    dependencies = serializers.CharField(read_only=True)

    def get_item(self, obj):
        return str(obj.item)

class ReferenceListItemSerializer(serializers.Serializer):
    source = serializers.CharField(read_only=True)
    target = serializers.CharField(read_only=True)
    target_candidate_count = serializers.IntegerField(read_only=True)
    dependencies = serializers.SerializerMethodField('get_dependencies')
    broken_count = serializers.IntegerField(read_only=True)
    deletable_count = serializers.IntegerField(read_only=True)
    broken_references = ReferenceSerializer()

    def get_dependencies(self, obj):
        dependencies = []
        for dependency in obj.reference_definition.dependencies:
            dependencies.append('%s.%s' % (dependency.source_type.__name__, dependency.source_field))
        return dependencies

class ReferenceListSerializer(serializers.Serializer):
    broken_total_count = serializers.IntegerField(read_only=True)
    deletable_total_count = serializers.IntegerField(read_only=True)
    items = ReferenceListItemSerializer()


class OclImportResultsSerializer(serializers.Serializer):
    summary = serializers.SerializerMethodField('get_detailed_summary')

    def get_detailed_summary(self, obj):
        return obj.get_detailed_summary()