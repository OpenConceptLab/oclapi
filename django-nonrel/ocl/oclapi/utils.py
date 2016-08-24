import json
import os
import tarfile
import tempfile

from boto.s3.key import Key
from boto.s3.connection import S3Connection
from haystack.utils import loading
from rest_framework.reverse import reverse
from rest_framework.utils import encoders
from django.conf import settings
from django.core.urlresolvers import NoReverseMatch

__author__ = 'misternando'

haystack_connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)


class S3ConnectionFactory:
    s3_connection = None

    @classmethod
    def get_s3_connection(cls):
        secure_connection = settings.AWS_PORT != settings.AWS_MOCK_PORT
        if not cls.s3_connection:
            if os.environ.get('DJANGO_CONFIGURATION') == 'Test':
                cls.s3_connection = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, secure_connection, host=settings.AWS_HOST, port=settings.AWS_PORT)
            else:
                cls.s3_connection = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        return cls.s3_connection

    @classmethod
    def get_export_bucket(cls):
        conn = cls.get_s3_connection()
        return conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)


def reverse_resource(resource, viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
    Generate the URL for the view specified as viewname of the object specified as resource.
    """
    kwargs = kwargs or {}
    parent = resource
    while parent is not None:
        if not hasattr(parent, 'get_url_kwarg'):
            return NoReverseMatch('Cannot get URL kwarg for %s' % resource)
        kwargs.update({parent.get_url_kwarg(): parent.mnemonic})
        parent = parent.parent if hasattr(parent, 'parent') else None
    return reverse(viewname, args, kwargs, request, format, **extra)


def reverse_resource_version(resource, viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
    Generate the URL for the view specified as viewname of the object that is versioned by the object specified as resource.
    Assumes that resource extends ResourceVersionMixin, and therefore has a versioned_object attribute.
    """
    kwargs = kwargs or {}
    kwargs.update({
        resource.get_url_kwarg(): resource.mnemonic
    })
    return reverse_resource(resource.versioned_object, viewname, args, kwargs, request, format, **extra)


def add_user_to_org(userprofile, organization):
    transaction_complete = False
    if not userprofile.id in organization.members:
        try:
            organization.members.append(userprofile.id)
            userprofile.organizations.append(organization.id)
            organization.save()
            userprofile.save()
            transaction_complete = True
        finally:
            if not transaction_complete:
                userprofile.organizations.remove(organization.id)
                organization.members.remove(userprofile.id)
                userprofile.save()
                organization.save()


def remove_user_from_org(userprofile, organization):
    transaction_complete = False
    if userprofile.id in organization.members:
        try:
            organization.members.remove(userprofile.id)
            userprofile.organizations.remove(organization.id)
            organization.save()
            userprofile.save()
            transaction_complete = True
        finally:
            if not transaction_complete:
                userprofile.organizations.add(organization.id)
                organization.members.add(userprofile.id)
                userprofile.save()
                organization.save()


def get_class(kls):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__(module)
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m


def write_export_file(version, logger):
    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    logger.info('Writing export file to tmp directory: %s' % tmpdir)

    logger.info('Found source version %s.  Looking up source...' % version.mnemonic)
    source = version.versioned_object
    logger.info('Found source %s.  Serializing attributes...' % source.mnemonic)

    source_serializer = get_class('sources.serializers.SourceDetailSerializer')(source)
    source_data = source_serializer.data
    source_string = json.dumps(source_data, cls=encoders.JSONEncoder)
    logger.info('Done serializing attributes.')

    with open('export.json', 'wb') as out:
        out.write('%s, "concepts": [' % source_string[:-1])

    batch_size = 1000

    num_concepts = len(version.concepts)
    if num_concepts:
        logger.info('Source has %d concepts.  Getting them in batches of %d...' % (num_concepts, batch_size))
        concept_version_class = get_class('concepts.models.ConceptVersion')
        concept_serializer_class = get_class('concepts.serializers.ConceptVersionDetailSerializer')
        for start in range(0, num_concepts, batch_size):
            end = min(start + batch_size, num_concepts)
            logger.info('Serializing concepts %d - %d...' % (start+1, end))
            concept_versions = concept_version_class.objects.filter(id__in=version.concepts[start:end], is_active=True)
            concept_serializer = concept_serializer_class(concept_versions, many=True)
            concept_data = concept_serializer.data
            concept_string = json.dumps(concept_data, cls=encoders.JSONEncoder)
            concept_string = concept_string[1:-1]
            with open('export.json', 'ab') as out:
                out.write(concept_string)
                if end != num_concepts:
                    out.write(', ')
        logger.info('Done serializing concepts.')
    else:
        logger.info('Source has no concepts to serialize.')

    with open('export.json', 'ab') as out:
        out.write('], "mappings": [')

    num_mappings = len(version.mappings)
    if num_mappings:
        logger.info('Source has %d mappings.  Getting them in batches of %d...' % (num_mappings, batch_size))
        mapping_class = get_class('mappings.models.Mapping')
        mapping_serializer_class = get_class('mappings.serializers.MappingDetailSerializer')
        for start in range(0, num_mappings, batch_size):
            end = min(start + batch_size, num_mappings)
            logger.info('Serializing mappings %d - %d...' % (start+1, end))
            mappings = mapping_class.objects.filter(id__in=version.mappings[start:end], is_active=True)
            mapping_serializer = mapping_serializer_class(mappings, many=True)
            mapping_data = mapping_serializer.data
            mapping_string = json.dumps(mapping_data, cls=encoders.JSONEncoder)
            mapping_string = mapping_string[1:-1]
            with open('export.json', 'ab') as out:
                out.write(mapping_string)
                if end != num_mappings:
                    out.write(', ')
        logger.info('Done serializing mappings.')
    else:
        logger.info('Source has no mappings to serialize.')

    with open('export.json', 'ab') as out:
        out.write(']}')

    with tarfile.open('export.tgz', 'w:gz') as tar:
        tar.add('export.json')

    logger.info('Done compressing.  Uploading...')
    k = Key(S3ConnectionFactory.get_export_bucket())
    k.key = version.export_path
    k.set_contents_from_filename('export.tgz')
    logger.info('Uploaded to %s.' % k.key)
    os.chdir(cwd)


def update_all_in_index(model, qs):
    if not qs.exists():
        return
    default_connection = haystack_connections['default']
    unified_index = default_connection.get_unified_index()
    index = unified_index.get_index(model)
    backend = default_connection.get_backend()
    do_update(default_connection, backend, index, qs)


def do_update(connection, backend, index, qs, batch_size=1000):
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)

        # Get a clone of the QuerySet so that the cache doesn't bloat up
        # in memory. Useful when reindexing large amounts of data.
        small_cache_qs = qs.all()
        current_qs = small_cache_qs[start:end]
        backend.update(index, current_qs)

        # Clear out the DB connections queries because it bloats up RAM.
        connection.queries = []
