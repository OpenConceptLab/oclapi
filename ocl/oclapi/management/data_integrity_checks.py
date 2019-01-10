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

