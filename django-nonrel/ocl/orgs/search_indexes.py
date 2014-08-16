from haystack import indexes
from oclapi.search_backends import SortField
from orgs.models import Organization

__author__ = 'misternando'


class OrganizationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = SortField(model_attr='name', indexed=True, stored=True)
    company = SortField(model_attr='company', null=True, indexed=True, stored=True)
    last_update = indexes.DateTimeField(model_attr='updated_at', indexed=True, stored=True)
    num_stars = indexes.IntegerField(model_attr='num_stars', indexed=True, stored=True)

    def get_model(self):
        return Organization
