from haystack import indexes
from oclapi.search_backends import SortField
from users.models import UserProfile

__author__ = 'misternando'


class UserProfileIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    username = SortField(model_attr='user__username', indexed=True, stored=True)
    company = SortField(model_attr='company', null=True, indexed=True, stored=True)
    location = SortField(model_attr='location', null=True, indexed=True, stored=True)
    date_joined = indexes.DateTimeField(model_attr='created_at', indexed=True, stored=True)
    num_stars = indexes.IntegerField(model_attr='num_stars', indexed=True, stored=True)

    def get_model(self):
        return UserProfile
