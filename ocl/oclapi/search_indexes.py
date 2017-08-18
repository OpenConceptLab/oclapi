from haystack.indexes import SearchIndex

__author__ = 'misternando'


class OCLSearchIndex(SearchIndex):

    def get_updated_field(self):
        return 'updated_at'
