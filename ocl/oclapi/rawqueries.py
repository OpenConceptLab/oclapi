from bson import ObjectId
from django.db import connections

from oclapi.utils import remove_from_search_index
from tasks import update_search_index_task


class RawQueries():

    db = connections['default']

    def bulk_delete(self, type, ids):
        collection = self.db.get_collection(type._meta.db_table)
        collection.remove({'_id': {'$in': [ObjectId(id) for id in ids]}})
        for id in ids:
            remove_from_search_index(type, id)

    def find_by_id(self, type, id):
        collection = self.db.get_collection(type._meta.db_table)
        item = collection.find_one({'_id': ObjectId(id)})
        return item

    def find_by_field(self, type, field, value):
        collection = self.db.get_collection(type._meta.db_table)
        items = collection.find({field: value})
        return items


    def delete_source_version(self, source_version):

        from mappings.models import MappingVersion
        mapping_version_ids = list(source_version.get_mapping_ids()) #store before deletion

        MappingVersion.objects.raw_update({}, {'$pull': {'source_version_ids': source_version.id}})

        update_search_index_task.delay(MappingVersion, MappingVersion.objects.filter(id__in=mapping_version_ids))

        from concepts.models import ConceptVersion
        concept_versions_ids = list(source_version.get_concept_ids()) #store before deletion

        ConceptVersion.objects.raw_update({}, {'$pull': {'source_version_ids': source_version.id}})

        update_search_index_task.delay(ConceptVersion, ConceptVersion.objects.filter(id__in=concept_versions_ids))


    def delete_source(self, source):
        from sources.models import SourceVersion

        source_version_ids = list(SourceVersion.objects.filter(versioned_object_id=source.id).values_list('id', flat=True))

        from mappings.models import MappingVersion
        mapping_version_ids = list(MappingVersion.objects.filter(source_version_ids__in=source_version_ids).values_list('id', flat=True))
        mapping_versions_col = self.db.get_collection('mappings_mappingversion')
        mapping_versions_col.remove({'_id': {'$in': [ObjectId(id) for id in mapping_version_ids]}})
        for mapping_version_id in mapping_version_ids:
            remove_from_search_index(MappingVersion, mapping_version_id)

        from mappings.models import Mapping
        mapping_ids = list(Mapping.objects.filter(parent_id=source.id).values_list('id', flat=True))
        mappings_col = self.db.get_collection('mappings_mapping')
        mappings_col.remove({ 'parent_id': ObjectId(source.id)})
        for mapping_id in mapping_ids:
            remove_from_search_index(Mapping, mapping_id)

        from concepts.models import ConceptVersion
        concept_version_ids = list(ConceptVersion.objects.filter(source_version_ids__in=source_version_ids).values_list('id', flat=True))
        concept_versions_col = self.db.get_collection('concepts_conceptversion')
        concept_versions_col.remove({'_id': {'$in': [ObjectId(id) for id in concept_version_ids]}})
        for concept_version_id in concept_version_ids:
            remove_from_search_index(ConceptVersion, concept_version_id)

        from concepts.models import Concept
        concept_ids = list(Concept.objects.filter(parent_id=source.id).values_list('id', flat=True))
        concepts_col = self.db.get_collection('concepts_concept')
        concepts_col.remove({'parent_id': source.id})
        for concept_id in concept_ids:
            remove_from_search_index(Concept, concept_id)

        source_versions_col = self.db.get_collection('sources_sourceversion')
        source_versions_col.remove({'versioned_object_id': source.id})
        for source_version_id in source_version_ids:
            remove_from_search_index(SourceVersion, source_version_id)

        sources_col = self.db.get_collection('sources_source')
        sources_col.remove({'_id': ObjectId(source.id)})

        from sources.models import Source
        remove_from_search_index(Source, source.id)
