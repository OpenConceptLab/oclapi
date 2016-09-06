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
from concepts.models import ConceptVersion
from mappings.models import Mapping
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
    write_export_file(version, 'source', 'sources.serializers.SourceDetailSerializer', logger)
    logger.info('Export complete!')

@celery.task(base=QueueOnce)
def export_collection(version_id):
    logger.info('Finding collection version...')
    version = CollectionVersion.objects.get(id=version_id)
    logger.info('Found collection version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, 'collection', 'collection.serializers.CollectionDetailSerializer', logger)
    logger.info('Export complete!')

@celery.task
def update_children_for_source_version(version_id):
    sv = SourceVersion.objects.get(id=version_id)
    sv._ocl_processing = True
    sv.save()
    versions = ConceptVersion.objects.filter(id__in=sv.concepts)
    update_all_in_index(ConceptVersion, versions)
    mappings = Mapping.objects.filter(id__in=sv.mappings)
    update_all_in_index(Mapping, mappings)
    sv._ocl_processing = False
    sv.save()
