import traceback

def update_concepts_and_mappings_count(logger):
    from collection.models import CollectionVersion
    from sources.models import SourceVersion
    logger.info('Updating concepts/mappings count and last updates on SourceVersions and CollectionVersions...')
    for source_version in SourceVersion.objects.all():
        try:
            source_version.save()
        except Exception:
            logger.error('Failed to update SourceVersion(%s) due to %s' % (source_version.id, traceback.format_exc()))
    for collection_version in CollectionVersion.objects.all():
        try:
            collection_version.save()
        except Exception:
            logger.error(
                'Failed to update CollectionVersion(%s) due to %s' % (collection_version.id, traceback.format_exc()))
    logger.info('Done updating concepts/mappings count and last updates on SourceVersions and CollectionVersions...')

def check_for_broken_references_in_collection_versions(logger):
    logger.info('Checking for broken concept and mapping references in collection versions')
    from collection.models import CollectionVersion
    for collection_version in CollectionVersion.objects.all():
        existing_concept_ids = list(collection_version.get_concepts().values_list('id', flat=True))
        from collection.models import CollectionConcept
        broken_concepts = CollectionConcept.objects.filter(collection_id=collection_version.id).exclude(concept_id__in=existing_concept_ids)
        if broken_concepts:
            logger.error('Removing %s broken concept references from collection version %s' %(broken_concepts.count(), collection_version.url))
            broken_concepts.delete()

        existing_mapping_ids = list(collection_version.get_mappings().values_list('id', flat=True))
        from collection.models import CollectionMapping
        broken_mappings = CollectionMapping.objects.filter(collection_id=collection_version.id).exclude(mapping_id__in=existing_mapping_ids)
        if broken_mappings:
            logger.error('Removing %s broken mapping references from collection version %s' %(broken_mappings.count(), collection_version.url))
            broken_mappings.delete()
    logger.info('Done checking for broken concept and mapping references in collection versions')

