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
from collection.models import CollectionVersion, CollectionReference
from concepts.views import ConceptVersionListView
from mappings.views import MappingListView

import json
from rest_framework.test import APIRequestFactory

celery = Celery('tasks', backend='redis://', broker='django://')
celery.config_from_object('django.conf:settings')

logger = get_task_logger('celery.worker')
celery.conf.ONCE_REDIS_URL = celery.conf.CELERY_RESULT_BACKEND


@celery.task(base=QueueOnce)
def export_source(version_id):
    logger.info('Finding source version...')
    version = SourceVersion.objects.get(id=version_id)
    logger.info('Found source version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, 'source', 'sources.serializers.SourceVersionExportSerializer', logger)
    logger.info('Export complete!')


@celery.task(base=QueueOnce)
def export_collection(version_id):
    logger.info('Finding collection version...')
    version = CollectionVersion.objects.get(id=version_id)
    logger.info('Found collection version %s.  Beginning export...' % version.mnemonic)
    write_export_file(version, 'collection', 'collection.serializers.CollectionVersionExportSerializer', logger)
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
        index_resource(concepts, Concept, ConceptVersion, 'mnemonic__in')

    if len(mappings) > 0:
        index_resource(mappings, Mapping, MappingVersion, 'id__in')

    cv._ocl_processing = False
    cv.save()


def get_related_mappings(expressions):
    mapping_expressions_without_version = \
        [drop_version(expression) for expression in expressions if 'mappings' in expression]
    mappings = []

    for expression in expressions:
        if expression.__contains__('concepts'):
            concept_id = get_concept_id_by_version_information(expression)
            concept_related_mappings = Mapping.objects.filter(from_concept_id=concept_id)

            for mapping in concept_related_mappings:
                if mapping.url not in mapping_expressions_without_version:
                    mappings.append(mapping.url)

    return mappings


def get_concept_id_by_version_information(expression):
    if CollectionReference.version_specified(expression):
        return ConceptVersion.objects.get(uri=expression).versioned_object_id
    else:
        return Concept.objects.get(uri=expression).id


def drop_version(expression):
    expression_parts_without_version = '/'.join(expression.split('/')[0:7]) + '/'
    return expression_parts_without_version


@celery.task
def add_references(SerializerClass, user, data, parent_resource, host_url):
    expressions = data.get('expressions', [])
    concept_expressions = data.get('concepts', [])
    mapping_expressions = data.get('mappings', [])
    uri = data.get('uri')
    search_term = data.get('search_term', '')

    if '*' in [concept_expressions, mapping_expressions]:
        ResourceContainer = SourceVersion if uri.split('/')[3] == 'sources' else CollectionVersion

    if concept_expressions == '*':
        url = host_url + uri + 'concepts?q=' + search_term + '&limit=0'
        view = ConceptVersionListView.as_view()
        request = APIRequestFactory().get(url)
        response = view(request)
        response.render()
        concepts_dict = json.loads(response.content)
        concept_uris = [c['url'] for c in concepts_dict]
        concepts = Concept.objects.filter(uri__in=concept_uris)
        expressions.extend(map(lambda c: c.uri, concepts))
    else:
        expressions.extend(concept_expressions)

    if mapping_expressions == '*':
        url = host_url + uri + 'mappings?q=' + search_term + '&limit=0'
        view = MappingListView.as_view()
        request = APIRequestFactory().get(url)
        response = view(request)
        response.render()
        mappings_dict = json.loads(response.content)
        mapping_uris = [c['url'] for c in mappings_dict]
        mappings = Mapping.objects.filter(uri__in=mapping_uris)
        expressions.extend(map(lambda m: m.uri, mappings))
    else:
        expressions.extend(mapping_expressions)

    expressions = set(expressions)

    valid_expressions = []

    for expression in expressions:
        ref = CollectionReference(expression=expression)
        try:
            parent_resource.validate(ref, expression)
            valid_expressions.append(expression)
        except Exception:
            continue

    mappings = get_related_mappings(valid_expressions)

    expressions = expressions.union(set(mappings))


    prev_refs = parent_resource.references
    save_kwargs = {
        'force_update': True, 'expressions': expressions, 'user': user
    }

    serializer = SerializerClass(parent_resource, partial=True)

    serializer.save(**save_kwargs)
    update_collection_in_solr.delay(
        serializer.object.get_head().id,
        CollectionReference.diff(serializer.object.references, prev_refs)
    )

    if 'references' in serializer.errors:
        serializer.object.save()

    diff = map(lambda ref: ref, CollectionReference.diff(serializer.object.references, prev_refs))

    errors = serializer.errors.get('references', [])
    return diff, errors


def index_resource(resource_ids, resource_klass, resource_version_klass, identifier):
    _resource_ids = resource_klass.objects.filter(id__in=resource_ids)
    resource_version_ids = list(set(resource_ids) - set(map(lambda m: m.id, _resource_ids)))
    version_ids = map(lambda r: r.get_latest_version.id, _resource_ids) + resource_version_ids
    kwargs = {}
    kwargs[identifier] = version_ids
    versions = resource_version_klass.objects.filter(**kwargs)
    update_all_in_index(resource_version_klass, versions)
