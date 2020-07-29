import urllib

from haystack.indexes import SearchIndex
from celery_haystack.indexes import CelerySearchIndex
from haystack.signals import BaseSignalProcessor
from haystack.exceptions import HaystackError
from django.db import models
import logging
__author__ = 'misternando'


class OCLSearchIndex(CelerySearchIndex):

    def get_updated_field(self):
        return 'updated_at'


    def prepare(self, obj):
        self.prepared_data = super(OCLSearchIndex, self).prepare(obj)

        self.prepare_extras(self.prepared_data, 'extras', obj.extras)

        return self.prepared_data

    def prepare_extras(self, extras, field_name, field_value):
        if field_value is not None:
            if isinstance(field_value, dict):
                for k, v in field_value.items():
                    encoded_field_name = field_name + '_' + encode_search_field_name(k)
                    self.prepare_extras(extras, encoded_field_name, v)
            elif isinstance(field_value, list) or isinstance(field_value, set) or isinstance(field_value, tuple):
                for item_value in field_value:
                    self.prepare_extras(extras, field_name, item_value)
            elif field_name in extras:
                extras[field_name].append(field_value)
            else:
                extras[field_name] = [field_value]

def encode_search_field_name(field_name):
    field_name = urllib.quote(field_name)
    field_name = field_name.replace('_5F', '%5F') #in case provided in solr format
    field_name = field_name.replace('_', '_5F')
    field_name = field_name.replace('.', '_2E')
    field_name = field_name.replace('-', '_2D')
    field_name = field_name.replace('~', '_7E')
    field_name = field_name.replace('%', '_')
    return field_name