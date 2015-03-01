from haystack import indexes
from oclapi.search_backends import SortOrFilterField
from orgs.models import Organization

__author__ = 'misternando'


class OrganizationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = SortOrFilterField(model_attr='name', indexed=True, stored=True)
    company = SortOrFilterField(model_attr='company', null=True, indexed=True, stored=True)
    location = SortOrFilterField(model_attr='location', null=True, indexed=True, stored=True)
    lastUpdate = indexes.DateTimeField(model_attr='updated_at', indexed=True, stored=True)
    is_active = indexes.BooleanField(model_attr='is_active', indexed=True, stored=True)

    def get_model(self):
        return Organization
