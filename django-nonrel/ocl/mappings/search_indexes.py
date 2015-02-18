from haystack import indexes
from mappings.models import Mapping
from oclapi.search_backends import SortOrFilterField, FilterField
from sources.models import SourceVersion

__author__ = 'misternando'


class MappingIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    external_id = SortOrFilterField(model_attr='external_id', indexed=True, stored=True, null=True)
    map_type = SortOrFilterField(model_attr='map_type', indexed=True, stored=True)
    from_source = SortOrFilterField(model_attr='from_source_shorthand', indexed=True, stored=True)
    to_source = SortOrFilterField(model_attr='to_source_shorthand', indexed=True, stored=True)
    from_concept = SortOrFilterField(model_attr='from_concept_shorthand', indexed=True, stored=True)
    to_concept = SortOrFilterField(model_attr='to_concept_shorthand', indexed=True, stored=True, null=True)
    source_version = FilterField()
    public_can_view = indexes.BooleanField(model_attr='public_can_view', indexed=True, stored=True)
    retired = indexes.BooleanField(model_attr='retired', indexed=True, stored=True)

    def get_model(self):
        return Mapping

    def prepare_source_version(self, obj):
        source_version_ids = []
        source = obj.parent
        source_versions = SourceVersion.objects.filter(
            versioned_object_id=source.id,
        )
        for sv in source_versions:
            if obj.id in sv.mappings:
                source_version_ids.append(sv.id)
        return source_version_ids

