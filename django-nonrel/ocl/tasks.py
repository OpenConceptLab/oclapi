from __future__ import absolute_import
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oclapi.settings.local')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Local')

# order of imports seems to matter. Do the django-configuration
# import first
from configurations import importer
importer.install()

from celery import Celery
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from concepts.models import ConceptVersion, Concept
from mappings.models import Mapping, MappingVersion
from oclapi.utils import update_all_in_index, write_export_file
from sources.models import SourceVersion
from collection.models import CollectionVersion

celery = Celery('tasks', backend='redis://', broker='django://')
celery.config_from_object('django.conf:settings')

logger = get_task_logger('celery.worker')
celery.conf.ONCE_REDIS_URL = celery.conf.CELERY_RESULT_BACKEND


@celery.task(base=QueueOnce)
def export_source(version_id):
    logger.info('Finding source version...')
    version = SourceVersion.objects.get(id=version_id)
    logger.info('Found source version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, 'source', 'sources.serializers.SourceVersionDetailSerializer', logger)
    logger.info('Export complete!')


@celery.task(base=QueueOnce)
def export_collection(version_id):
    logger.info('Finding collection version...')
    version = CollectionVersion.objects.get(id=version_id)
    logger.info('Found collection version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, 'collection', 'collection.serializers.CollectionVersionDetailSerializer', logger)
    logger.info('Export complete!')


@celery.task
def update_children_for_resource_version(version_id, _type):
    _resource = resource(version_id, _type)
    _resource._ocl_processing = True
    _resource.save()
    versions = ConceptVersion.objects.filter(id__in=_resource.concepts)
    update_all_in_index(ConceptVersion, versions)
    mappingVersions = MappingVersion.objects.filter(id__in=_resource.mappings)
    update_all_in_index(MappingVersion, mappingVersions)
    _resource._ocl_processing = False
    _resource.save()


def resource(version_id, type):
    if type == 'source':
        return SourceVersion.objects.get(id=version_id)
    elif type == 'collection':
        return CollectionVersion.objects.get(id=version_id)


@celery.task
def update_collection_in_solr(version_id, references):
    cv = CollectionVersion.objects.get(id=version_id)
    cv._ocl_processing = True
    cv.save()
    concepts, mappings = [], [],

    for ref in references:
        if len(ref.concepts) > 0:
            concepts += ref.concepts
        if ref.mappings and len(ref.mappings) > 0:
            mappings += ref.mappings

    concept_versions = ConceptVersion.objects.filter(mnemonic__in=_get_version_ids(concepts, 'Concept'))
    mapping_versions = MappingVersion.objects.filter(id__in=_get_version_ids(mappings, 'Mapping'))

    if len(concept_versions) > 0:
        update_all_in_index(ConceptVersion, concept_versions)

    if len(mapping_versions) > 0:
        update_all_in_index(MappingVersion, mapping_versions)

    cv._ocl_processing = False
    cv.save()


def _get_version_ids(resources, klass):
    return map(lambda c: c.get_latest_version.id if type(c).__name__ == klass else c.id, resources)


@celery.task
def delete_resources_from_collection_in_solr(version_id, concepts, mappings):
    cv = CollectionVersion.objects.get(id=version_id)
    cv._ocl_processing = True
    cv.save()

    if len(concepts) > 0:
        concepts = Concept.objects.filter(id__in=concepts)
        version_ids = map(lambda c: c.get_latest_version.id, concepts)
        versions = ConceptVersion.objects.filter(mnemonic__in=version_ids)
        update_all_in_index(ConceptVersion, versions)

    if len(mappings) > 0:
        mappings = Mapping.objects.filter(id__in=mappings)
        version_ids = map(lambda m: m.get_latest_version.id, mappings)
        versions = MappingVersion.objects.filter(id__in=version_ids)
        update_all_in_index(MappingVersion, versions)

    cv._ocl_processing = False
    cv.save()
