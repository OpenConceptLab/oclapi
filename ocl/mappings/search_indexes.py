from haystack import indexes
from mappings.models import Mapping, MappingVersion
from oclapi.search_backends import SortOrFilterField, FilterField
from oclapi.search_indexes import OCLSearchIndex
from sources.models import SourceVersion
from django.db.models import get_model

__author__ = 'misternando'

class MappingVersionIndex(OCLSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    external_id = SortOrFilterField(model_attr='external_id', indexed=True, stored=True, null=True)
    lastUpdate = indexes.DateTimeField(model_attr='updated_at', indexed=True, stored=True)
    retired = indexes.BooleanField(model_attr='retired', indexed=True, stored=True, faceted=True)
    mapType = SortOrFilterField(model_attr='map_type', indexed=True, stored=True, faceted=True)
    source = SortOrFilterField(model_attr='source', indexed=True, stored=True, faceted=True)
    owner = SortOrFilterField(model_attr='owner', indexed=True, stored=True, faceted=True)
    ownerType = SortOrFilterField(model_attr='owner_type', indexed=True, stored=True, faceted=True)
    concept = FilterField(indexed=True, stored=True, faceted=True)
    fromConcept = FilterField(indexed=True, stored=True, faceted=True)
    toConcept = FilterField(indexed=True, stored=True, null=True, faceted=True)
    conceptSource = FilterField(indexed=True, stored=True, faceted=True)
    fromConceptSource = SortOrFilterField(indexed=True, stored=True, faceted=True)
    toConceptSource = SortOrFilterField(indexed=True, stored=True, faceted=True)
    conceptOwner = FilterField(faceted=True)
    fromConceptOwner = SortOrFilterField(indexed=True, stored=True, faceted=True)
    toConceptOwner = SortOrFilterField(indexed=True, stored=True, faceted=True)
    conceptOwnerType = FilterField(faceted=True)
    fromConceptOwnerType = SortOrFilterField(indexed=True, stored=True, faceted=True)
    toConceptOwnerType = SortOrFilterField(indexed=True, stored=True, faceted=True)
    source_version = FilterField()
    collection = FilterField()
    collection_version = FilterField()
    public_can_view = indexes.BooleanField(model_attr='public_can_view', indexed=True, stored=True)
    is_active = indexes.BooleanField(model_attr='is_active', indexed=True, stored=True)
    is_latest_version = indexes.BooleanField(model_attr='is_latest_version', indexed=True, stored=True)

    def get_model(self):
        return MappingVersion

    def prepare(self, obj):
        self.prepared_data = super(MappingVersionIndex, self).prepare(obj)
        self.prepared_data['fromConcept'] = [obj.from_concept_url, obj.from_concept_code, obj.from_concept_name]
        self.prepared_data['toConcept'] = [obj.get_to_concept_code(), obj.get_to_concept_name()]
        self.prepared_data['concept'] = self.prepared_data['fromConcept'] + self.prepared_data['toConcept']
        self.prepared_data['fromConceptSource'] = obj.from_source_name
        self.prepared_data['toConceptSource'] = obj.to_source_name
        self.prepared_data['conceptSource'] = [obj.from_source_name, obj.to_source_name]
        self.prepared_data['fromConceptOwner'] = obj.from_source_owner
        self.prepared_data['toConceptOwner'] = obj.to_source_owner
        self.prepared_data['conceptOwner'] = [obj.from_source_owner, obj.to_source_owner]
        self.prepared_data['fromConceptOwnerType'] = obj.from_source_owner_type
        self.prepared_data['toConceptOwnerType'] = obj.to_source_owner_type
        self.prepared_data['conceptOwnerType'] = [obj.from_source_owner_type, obj.to_source_owner_type]
        self.prepared_data['source_version'] = list(obj.source_version_ids)

        return self.prepared_data


    def prepare_collection_version(self, obj):
        return obj.get_collection_version_ids()


    def prepare_collection(self, obj):
        return obj.get_collection_ids()