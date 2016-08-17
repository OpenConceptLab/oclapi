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
from concepts.models import ConceptVersion
from mappings.models import Mapping
from oclapi.utils import update_all_in_index, write_export_file
from sources.models import SourceVersion

celery = Celery('tasks', backend='mongodb', broker='django://')
celery.config_from_object('django.conf:settings')

logger = get_task_logger('celery.worker')

@celery.task
def export_source(version_id):
    logger.info('Finding source version...')
    version = SourceVersion.objects.get(id=version_id)
    logger.info('Found source version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, logger)
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
