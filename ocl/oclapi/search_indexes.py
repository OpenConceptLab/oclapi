import urllib

from haystack.indexes import SearchIndex

__author__ = 'misternando'


class OCLSearchIndex(SearchIndex):

    def get_updated_field(self):
        return 'updated_at'


    def prepare(self, obj):
        self.prepared_data = super(OCLSearchIndex, self).prepare(obj)

        self.prepare_extras(self.prepared_data, 'extras', obj.extras)

        return self.prepared_data

    def prepare_extras(self, extras, field_name, field_value):
        if field_value:
            for k, v in field_value.items():
                if isinstance(v, dict):
                    encoded_field_name = encode_search_field_name(k)
                    self.prepare_extras(extras, field_name + '_' + encoded_field_name, v)
                elif isinstance(v, list) or isinstance(v, set) or isinstance(v, tuple):
                    pass #collections are not indexed
                else:
                    encoded_field_name = encode_search_field_name(k)
                    extras[field_name + '_' + encoded_field_name] = v

def encode_search_field_name(field_name):
    field_name = urllib.quote(field_name)
    field_name = field_name.replace('_', '_5F')
    field_name = field_name.replace('.', '_2E')
    field_name = field_name.replace('-', '_2D')
    field_name = field_name.replace('~', '_7E')
    field_name = field_name.replace('%', '_')
    return field_name