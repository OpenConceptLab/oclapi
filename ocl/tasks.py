from __future__ import absolute_import

import os

from oclapi.management.data_integrity_checks import update_concepts_and_mappings_count, \
    check_for_broken_references_in_collection_versions

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oclapi.settings.local')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Local')

# order of imports seems to matter. Do the django-configuration
# import first
from configurations import importer

importer.install()

from celery import Celery
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from oclapi.utils import update_all_in_index, write_export_file

import json
from rest_framework.test import APIRequestFactory

celery = Celery('tasks', backend='redis://', broker='django://')
celery.config_from_object('django.conf:settings')

logger = get_task_logger(__name__)
celery.conf.ONCE_REDIS_URL = celery.conf.CELERY_RESULT_BACKEND

@celery.task(base=QueueOnce, bind=True)
def data_integrity_checks(self):
    check_for_broken_references_in_collection_versions(logger)
    update_concepts_and_mappings_count(logger)

@celery.task(base=QueueOnce, bind=True)
def export_source(self, version_id):
    from sources.models import SourceVersion

    logger.info('Finding source version...')

    version = SourceVersion.objects.get(id=version_id)
    version.add_processing(self.request.id)
    try:
        logger.info('Found source version %s.  Beginning export...' % version.mnemonic)
        write_export_file(version, 'source', 'sources.serializers.SourceVersionExportSerializer', logger)
        logger.info('Export complete!')
    finally:
        version.remove_processing(self.request.id)


@celery.task(base=QueueOnce, bind=True)
def export_collection(self, version_id):
    from collection.models import CollectionVersion
    logger.info('Finding collection version...')
    version = CollectionVersion.objects.get(id=version_id)
    version.add_processing(self.request.id)
    try:
        logger.info('Found collection version %s.  Beginning export...' % version.mnemonic)
        write_export_file(version, 'collection', 'collection.serializers.CollectionVersionExportSerializer', logger)
        logger.info('Export complete!')
    finally:
        version.remove_processing(self.request.id)

@celery.task(bind = True)
def update_children_for_resource_version(self, version_id, _type):
    from concepts.models import ConceptVersion
    from mappings.models import MappingVersion

    _resource = resource(version_id, _type)
    _resource.add_processing(self.request.id)
    try:
        concept_versions = _resource.get_concepts()
        mapping_versions = _resource.get_mappings()

        logger.info('Indexing %s concepts...' % concept_versions.count())

        update_all_in_index(ConceptVersion, concept_versions)
        logger.info('Indexing %s mappings...' % mapping_versions.count())

        update_all_in_index(MappingVersion, mapping_versions)

    finally:
        _resource.remove_processing(self.request.id)

@celery.task(bind = True)
def update_search_index_task(self, model, query):
    logger.info('Updating search index for %s...' % model.__name__)
    update_all_in_index(model, query)

def resource(version_id, type):
    from sources.models import SourceVersion
    from collection.models import CollectionVersion
    if type == 'source':
        return SourceVersion.objects.get(id=version_id)
    elif type == 'collection':
        return CollectionVersion.objects.get(id=version_id)


@celery.task(bind = True)
def update_collection_in_solr(self, version_id, references):
    from concepts.models import ConceptVersion
    from mappings.models import MappingVersion
    from collection.models import CollectionVersion

    version = CollectionVersion.objects.get(id=version_id)
    version.add_processing(self.request.id)
    try:
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
    finally:
        version.remove_processing(self.request.id)


def _get_version_ids(resources, klass):
    return map(lambda c: c.get_latest_version.id if type(c).__name__ == klass else c.id, resources)


@celery.task(bind = True)
def delete_resources_from_collection_in_solr(self, version_id, concepts, mappings):
    from concepts.models import Concept
    from mappings.models import Mapping
    from concepts.models import ConceptVersion
    from mappings.models import MappingVersion
    from collection.models import CollectionVersion

    version = CollectionVersion.objects.get(id=version_id)
    version.add_processing(self.request.id)
    try:
        if len(concepts) > 0:
            index_resource(concepts, Concept, ConceptVersion, 'mnemonic__in')

        if len(mappings) > 0:
            index_resource(mappings, Mapping, MappingVersion, 'id__in')
    finally:
        version.remove_processing(self.request.id)


@celery.task
def add_references(SerializerClass, user, data, parent_resource, host_url, cascade_mappings=False):
    from concepts.models import Concept
    from mappings.models import Mapping
    from collection.models import CollectionVersion
    from sources.models import SourceVersion
    from concepts.views import ConceptVersionListView
    from mappings.views import MappingListView
    from collection.models import CollectionReferenceUtils
    from collection.models import CollectionReference

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

    if cascade_mappings:
        all_related_mappings = CollectionReferenceUtils.get_all_related_mappings(expressions, parent_resource)
        expressions = expressions.union(set(all_related_mappings))

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
