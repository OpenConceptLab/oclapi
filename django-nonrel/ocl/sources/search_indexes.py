from haystack import indexes
from oclapi.search_backends import SortOrFilterField, FilterField
from sources.models import Source

__author__ = 'misternando'


class SourceIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = SortOrFilterField(model_attr='name', indexed=True, stored=True)
    full_name = indexes.CharField(model_attr='full_name', null=True, indexed=True, stored=True)
    lastUpdate = indexes.DateTimeField(model_attr='updated_at', indexed=True, stored=True)
    sourceType = SortOrFilterField(model_attr='source_type', null=True, indexed=True, stored=True, faceted=True)
    locale = FilterField(model_attr='supported_locales', null=True, indexed=True, stored=True, faceted=True)
    owner = SortOrFilterField(model_attr='owner_name', indexed=True, stored=True, faceted=True)
    ownerType = SortOrFilterField(model_attr='owner_type', indexed=True, stored=True, faceted=True)
    is_active = indexes.BooleanField(model_attr='is_active', indexed=True, stored=True)

    def get_model(self):
        return Source
