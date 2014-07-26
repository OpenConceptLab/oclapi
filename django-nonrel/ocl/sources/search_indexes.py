from haystack import indexes
from sources.models import Source

__author__ = 'misternando'


class SourceIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=True, stored=True)
    full_name = indexes.CharField(model_attr='full_name', null=True, indexed=True, stored=True)
    source_type = indexes.CharField(model_attr='source_type', null=True, indexed=True, stored=True)

    def get_model(self):
        return Source



