import json
import os
import tarfile
import tempfile
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from bson import json_util
from celery import Celery
from celery.utils.log import get_task_logger
from django.conf import settings
from concepts.models import ConceptVersion
from concepts.serializers import ConceptVersionDetailSerializer
from mappings.models import Mapping
from mappings.serializers import MappingDetailSerializer
from sources.models import SourceVersion
from sources.serializers import SourceDetailSerializer

celery = Celery('tasks', backend='mongodb', broker='django://')
logger = get_task_logger(__name__)

@celery.task
def export_source(version_id):
    logger.info("Getting S3 connection...")
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    logger.info("Getting export bucket...")
    bucket = conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)
    k = Key(bucket)


    logger.info('Finding source version...')
    version = SourceVersion.objects.get(id=version_id)
    logger.info('Found source version %s.  Looking up source...' % version.mnemonic)
    source = version.versioned_object
    logger.info('Found source %s.  Exporting...' % source.mnemonic)
    last_update = version.updated_at.strftime('%Y%m%d%H%M%S')
    k.key = "%s/%s_%s_%s.tgz" % (source.owner_name, source.mnemonic, version.mnemonic, last_update)

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
        json.dump(data, out, default=json_util.default)
    logger.info('Done writing export file.  Compressing...')
    with tarfile.open('export.tgz', 'w:gz') as tar:
        tar.add('export.json')
    logger.info('Done compressing.  Uploading...')
    k.set_contents_from_filename('export.tgz')
    os.chdir(cwd)
    logger.info('Export complete!')



