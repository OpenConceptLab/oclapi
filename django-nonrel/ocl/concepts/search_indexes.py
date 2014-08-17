from django.contrib.contenttypes.models import ContentType
from haystack import indexes
from haystack.fields import MultiValueField
from concepts.models import ConceptVersion
from oclapi.search_backends import SortOrFilterField
from sources.models import SourceVersion, Source

__author__ = 'misternando'


class ConceptVersionIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = SortOrFilterField(model_attr='name', indexed=True, stored=True)
    last_update = indexes.DateTimeField(model_attr='updated_at', indexed=True, stored=True)
    num_stars = indexes.IntegerField(model_attr='versioned_object__num_stars', indexed=True, stored=True)
    source_version = MultiValueField()

    def get_model(self):
        return ConceptVersion

    def prepare_source_version(self, obj):
        source_version_ids = []
        source = obj.source
        source_versions = SourceVersion.objects.filter(
            versioned_object_id=source.id,
            versioned_object_type=ContentType.objects.get_for_model(Source)
        )
        for sv in source_versions:
            if obj.id in sv.concepts:
                source_version_ids.append(sv.id)
        return source_version_ids




