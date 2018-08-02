from bson import ObjectId
from django.db import connections

class RawQueries():

    db = connections['default']

    def delete_source(self, source):
        from sources.models import SourceVersion

        source_version_ids = list(SourceVersion.objects.filter(versioned_object_id=source.id).values_list('id', flat=True))
        mapping_versions_col = self.db.get_collection('mappings_mappingversion')
        mapping_versions_col.remove({'source_version_ids': {'$in': source_version_ids}})

        mappings_col = self.db.get_collection('mappings_mapping')
        mappings_col.remove({ 'parent_id': ObjectId(source.id)})

        concept_versions_col = self.db.get_collection('concepts_conceptversion')
        concept_versions_col.remove({'source_version_ids': {'$in': source_version_ids}})

        concepts_col = self.db.get_collection('concepts_concept')
        concepts_col.remove({'parent_id': source.id})

        source_versions_col = self.db.get_collection('sources_sourceversion')
        source_versions_col.remove({'versioned_object_id': source.id})

        sources_col = self.db.get_collection('sources_source')
        sources_col.remove({'_id': ObjectId(source.id)})
