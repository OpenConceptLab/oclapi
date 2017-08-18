from haystack import indexes
from oclapi.search_backends import SortOrFilterField
from oclapi.search_indexes import OCLSearchIndex
from users.models import UserProfile

__author__ = 'misternando'


class UserProfileIndex(OCLSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    username = SortOrFilterField(model_attr='user__username', indexed=True, stored=True)
    company = SortOrFilterField(model_attr='company', null=True, indexed=True, stored=True)
    location = SortOrFilterField(model_attr='location', null=True, indexed=True, stored=True)
    dateJoined = indexes.DateTimeField(model_attr='created_at', indexed=True, stored=True)
    is_active = indexes.BooleanField(model_attr='is_active', indexed=True, stored=True)

    def get_model(self):
        return UserProfile
