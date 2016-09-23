import json
import os
import tarfile
import tempfile
import gzip

from boto.s3.key import Key
from boto.s3.connection import S3Connection
from haystack.utils import loading
from rest_framework.reverse import reverse
from rest_framework.utils import encoders
from django.conf import settings
from django.core.urlresolvers import NoReverseMatch
from operator import is_not, itemgetter
from djqscsv import csv_file_for



__author__ = 'misternando'

haystack_connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)


class S3ConnectionFactory:
    s3_connection = None

    @classmethod
    def get_s3_connection(cls):
        if not cls.s3_connection:
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
    val = None
    if resource.mnemonic and resource.mnemonic != '':
        val = resource.mnemonic
    kwargs.update({
        resource.get_url_kwarg(): val
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


def write_export_file(version, resource_type, resource_serializer_type, logger):
    cwd = cd_temp()
    logger.info('Writing export file to tmp directory: %s' % tmpdir)

    logger.info('Found %s version %s.  Looking up resource...' % (resource_type, version.mnemonic))
    resource = version.versioned_object
    logger.info('Found %s %s.  Serializing attributes...' % (resource_type, resource.mnemonic))

    resource_serializer = get_class(resource_serializer_type)(version)
    data = resource_serializer.data
    resource_string = json.dumps(data, cls=encoders.JSONEncoder)
    logger.info('Done serializing attributes.')

    with open('export.json', 'wb') as out:
        out.write('%s, "concepts": [' % resource_string[:-1])

    batch_size = 1000
    active_concepts = resource_serializer.object.active_concepts
    if active_concepts:
        logger.info('%s has %d concepts.  Getting them in batches of %d...' % (resource_type.title(), active_concepts, batch_size))
        concept_version_class = get_class('concepts.models.ConceptVersion')
        concept_serializer_class = get_class('concepts.serializers.ConceptVersionDetailSerializer')
        for start in range(0, active_concepts, batch_size):
            end = min(start + batch_size, active_concepts)
            logger.info('Serializing concepts %d - %d...' % (start+1, end))
            concept_versions = concept_version_class.objects.filter(id__in=version.concepts[start:end], is_active=True)
            concept_serializer = concept_serializer_class(concept_versions, many=True)
            concept_data = concept_serializer.data
            concept_string = json.dumps(concept_data, cls=encoders.JSONEncoder)
            concept_string = concept_string[1:-1]
            with open('export.json', 'ab') as out:
                out.write(concept_string)
                if end != active_concepts:
                    out.write(', ')
        logger.info('Done serializing concepts.')
    else:
        logger.info('%s has no concepts to serialize.' % (resource_type.title()))

    with open('export.json', 'ab') as out:
        out.write('], "mappings": [')

    active_mappings = resource_serializer.object.active_mappings
    if active_mappings:
        logger.info('%s has %d mappings.  Getting them in batches of %d...' % (resource_type.title(), active_mappings, batch_size))
        mapping_class = get_class('mappings.models.Mapping')
        mapping_serializer_class = get_class('mappings.serializers.MappingDetailSerializer')
        for start in range(0, active_mappings, batch_size):
            end = min(start + batch_size, active_mappings)
            logger.info('Serializing mappings %d - %d...' % (start+1, end))
            mappings = mapping_class.objects.filter(id__in=version.mappings[start:end], is_active=True)
            mapping_serializer = mapping_serializer_class(mappings, many=True)
            mapping_data = mapping_serializer.data
            mapping_string = json.dumps(mapping_data, cls=encoders.JSONEncoder)
            mapping_string = mapping_string[1:-1]
            with open('export.json', 'ab') as out:
                out.write(mapping_string)
                if end != active_mappings:
                    out.write(', ')
        logger.info('Done serializing mappings.')
    else:
        logger.info('%s has no mappings to serialize.' % (resource_type.title()))

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


def write_csv_to_s3(data, is_owner, **kwargs):
    cwd = cd_temp()
    csv_file = csv_file_for(data, **kwargs)
    csv_file.close()
    reader = open(os.path.abspath(csv_file.name), 'r')
    gz = gzip.open(csv_file.name + '.gz', 'wb')
    lines = reader.readlines()
    gz.writelines(lines)
    gz.close()
    reader.close()

    bucket = S3ConnectionFactory.get_export_bucket()
    k = Key(bucket)
    _dir = 'downloads/creator/' if is_owner else 'downloads/reader/'
    k.key = _dir + gz.name
    k.set_metadata('Content-Encoding', 'gzip')
    k.set_metadata('Content-Type', 'text/csv')
    k.set_contents_from_filename(gz.name)

    os.chdir(cwd)
    return bucket.get_key(k.key).generate_url(expires_in=60)


def get_csv_from_s3(filename, is_owner):
    _dir = 'downloads/creator' if is_owner else 'downloads/reader'
    filename = _dir + filename + '.csv.gz'
    bucket = S3ConnectionFactory.get_export_bucket()
    key = bucket.get_key(filename)
    return key.generate_url(expires_in=600) if key else None


def cd_temp():
    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)
    return cwd


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


def compact(_list):
    return filter(None, _list)


def extract_values(_dict, keys):
    values = itemgetter(*keys)(_dict)
    values = values if type(values).__name__ == 'tuple'  or type(values).__name__ == 'list' else [values]
    return list(values)