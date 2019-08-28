from django.core.management import BaseCommand
from django.db import connections

from oclapi.models import ConceptContainerVersionModel
from sources.models import SourceVersion
from collection.models import CollectionVersion, CollectionConcept, CollectionMapping

class Command(BaseCommand):
    help = 'run before startup'

    def handle(self, *args, **options):
        self.run_db_migrations()

        self.clear_all_processing()


    def run_db_migrations(self):
        db = connections['default']
        print 'Deleting concepts and mappings fields from SourceVersion'
        db.get_collection('sources_sourceversion').update({},{'$unset': {'concepts':1, 'mappings':1}}, multi=True)

        print 'Deleting _ocl_processing from SourceVersion'
        db.get_collection('sources_sourceversion').update({},{'$unset': {'_ocl_processing':1}}, multi=True)
        print 'Deleting _ocl_processing from CollectionVersion'
        db.get_collection('collection_collectionversion').update({},{'$unset': {'_ocl_processing':1}}, multi=True)

        print 'Migrating concepts and mappings in collections to a new model'
        collection_versions_count = CollectionVersion.objects.all().count()
        collection_versions_processed = 0
        for collection_version in CollectionVersion.objects.all().values('id', 'concepts', 'mappings'):
            uniqueConcepts = set(collection_version['concepts'])
            for concept in uniqueConcepts:
                CollectionConcept(collection_id=collection_version['id'], concept_id=concept).save()
            uniqueMappings = set(collection_version['mappings'])
            for mapping in uniqueMappings:
                CollectionMapping(collection_id=collection_version['id'], mapping_id=mapping).save()

            CollectionVersion.objects.filter(id=collection_version['id']).update(concepts=[], mappings=[])
            collection_versions_processed += 1
            print 'Migrated %d out of %d' % (collection_versions_processed, collection_versions_count)

    def clear_all_processing(self):
        ConceptContainerVersionModel.clear_all_processing(SourceVersion)
        ConceptContainerVersionModel.clear_all_processing(CollectionVersion)
