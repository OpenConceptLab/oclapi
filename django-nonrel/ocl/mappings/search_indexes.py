from haystack import indexes
from mappings.models import Mapping
from oclapi.search_backends import SortOrFilterField

__author__ = 'misternando'


class MappingIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    map_type = SortOrFilterField(model_attr='map_type', indexed=True, stored=True)
    from_source = SortOrFilterField(model_attr='from_source_shorthand', indexed=True, stored=True)
    to_source = SortOrFilterField(model_attr='to_source_shorthand', indexed=True, stored=True)
    from_concept = SortOrFilterField(model_attr='from_concept_shorthand', indexed=True, stored=True)
    to_concept = SortOrFilterField(model_attr='to_concept_shorthand', indexed=True, stored=True, null=True)

    def get_model(self):
        return Mapping
