from django.contrib.contenttypes.models import ContentType
from haystack import indexes
from concepts.models import ConceptVersion
from oclapi.search_backends import SortOrFilterField, FilterField
from oclapi.search_indexes import OCLSearchIndex
from sources.models import SourceVersion, Source

__author__ = 'misternando'


class ConceptVersionIndex(OCLSearchIndex, indexes.Indexable):
    text = indexes.CharField(
        document=True, use_template=True)
    name = SortOrFilterField(
        model_attr='display_name', indexed=True, stored=True, default="")
    lastUpdate = indexes.DateTimeField(
        model_attr='updated_at', indexed=True, stored=True)
    num_stars = indexes.IntegerField(
        model_attr='versioned_object__num_stars', indexed=True, stored=True)
    conceptClass = SortOrFilterField(
        model_attr='concept_class', indexed=True, stored=True, faceted=True)
    datatype = SortOrFilterField(
        model_attr='datatype', null=True, indexed=True, stored=True, faceted=True)
    locale = FilterField(
        indexed=True, stored=True, faceted=True)
    is_latest_version = indexes.BooleanField(
        model_attr='is_latest_version', indexed=True, stored=True)
    public_can_view = indexes.BooleanField(
        model_attr='public_can_view', indexed=True, stored=True)
    retired = indexes.BooleanField(
        model_attr='retired', indexed=True, stored=True, faceted=True)
    source = SortOrFilterField(model_attr='parent_resource', indexed=True, stored=True, faceted=True)
    owner = SortOrFilterField(
        model_attr='owner_name', indexed=True, stored=True, faceted=True)
    ownerType = SortOrFilterField(
        model_attr='owner_type', indexed=True, stored=True, faceted=True)
    source_version = FilterField()
    collection = FilterField()
    collection_version = FilterField()
    is_active = indexes.BooleanField(model_attr='is_active', indexed=True, stored=True)

    def get_model(self):
        return ConceptVersion

    def prepare_locale(self, obj):
        locales = set()
        if obj.names:
            for name in obj.names:
                if name.locale is not None:
                    locales.add(name.locale)
        return list(locales)

    def prepare_source_version(self, obj):
        source_version_ids = list(SourceVersion.get_concept_sources(obj.id).values_list('id', flat=True))
        return source_version_ids

    def prepare_collection_version(self, obj):
        return obj.collection_version_ids

    def prepare_collection(self, obj):
        return obj.collection_ids
