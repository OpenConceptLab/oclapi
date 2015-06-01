from __future__ import absolute_import
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Local")

# order of imports seems to matter. Do the django-configuration
# import first
from configurations import importer
importer.install()

import json
import tarfile
import tempfile
from rest_framework.utils import encoders
from boto.s3.key import Key
from bson import json_util
from celery import Celery
from celery.utils.log import get_task_logger
from concepts.models import ConceptVersion
from concepts.serializers import ConceptVersionDetailSerializer
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from oclapi.utils import S3ConnectionFactory, update_all_in_index
from sources.models import SourceVersion

celery = Celery('tasks', backend='mongodb', broker='django://')
celery.config_from_object('django.conf:settings')

logger = get_task_logger('celery')

@celery.task
def export_source(version_id):
    # otherwise circular import problem
    from sources.serializers import SourceDetailSerializer

    logger.info('Finding source version...')
    version = SourceVersion.objects.get(id=version_id)
    logger.info('Found source version %s.  Looking up source...' % version.mnemonic)
    source = version.versioned_object
    logger.info('Found source %s.  Exporting...' % source.mnemonic)

    logger.info('Serializing source attributes...')
    serializer = SourceDetailSerializer(source)
    data = serializer.data

    logger.info('Finding source concepts...')
    concept_versions = ConceptVersion.objects.filter(id__in=version.concepts, is_active=True)
    logger.info('Found %d concepts.  Serializing...' % concept_versions.count())
    serializer = ConceptVersionDetailSerializer(concept_versions, many=True)
    data['concepts'] = serializer.data

    logger.info('Finding source mappings...')
    mappings = Mapping.objects.filter(id__in=version.mappings, is_active=True)
    logger.info('Found %d mappings.  Serializing...' % mappings.count())
    serializer = MappingDetailSerializer(mappings, many=True)
    data['mappings'] = serializer.data

    logger.info('Done serializing.  Writing export file...')

    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    with open('export.json', 'wb') as out:
        json.dump(data, out, cls=encoders.JSONEncoder, default=json_util.default)
    logger.info('Done writing export file.  Compressing...')
    with tarfile.open('export.tgz', 'w:gz') as tar:
        tar.add('export.json')
    logger.info('Done compressing.  Uploading...')
    k = Key(S3ConnectionFactory.get_export_bucket())
    k.key = version.export_path
    k.set_contents_from_filename('export.tgz')
    os.chdir(cwd)
    logger.info('Export complete!')


@celery.task
def update_concepts_for_source_version(version_id):
    sv = SourceVersion.objects.get(id=version_id)
    sv._ocl_processing = True
    sv.save()
    versions = ConceptVersion.objects.filter(id__in=sv.concepts)
    update_all_in_index(ConceptVersion, versions)
    sv._ocl_processing = False
    sv.save()
