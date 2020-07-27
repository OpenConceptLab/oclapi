from __future__ import absolute_import

import os
import random
import uuid

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template import Context
from django.template.loader import render_to_string
from requests.auth import HTTPBasicAuth

from oclapi.management.data_integrity_checks import update_concepts_and_mappings_count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oclapi.settings.local')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Local')

# order of imports seems to matter. Do the django-configuration
# import first
from configurations import importer

importer.install()

from celery import Celery
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from oclapi.utils import update_all_in_index, write_export_file, timestamp_sign

import json
from rest_framework.test import APIRequestFactory

logger = get_task_logger(__name__)

celery = Celery('tasks', backend='redis://', broker='django://')
celery.config_from_object('django.conf:settings')
celery.conf.ONCE_REDIS_URL = celery.conf.CELERY_RESULT_BACKEND
celery.conf.CELERY_TASK_RESULT_EXPIRES = 259200 #72 hours
celery.conf.CELERY_TRACK_STARTED = True
celery.conf.CELERY_CREATE_MISSING_QUEUES = True

BULK_IMPORT_QUEUES_COUNT = 5

@celery.task(base=QueueOnce, bind=True)
def data_integrity_checks(self):
    update_concepts_and_mappings_count(logger)

@celery.task(base=QueueOnce, bind=True)
def find_broken_references(self):
    from manage.models import Reference
    broken_references = Reference.find_broken_references()
    return broken_references

def queue_bulk_import(to_import, import_queue, username, update_if_exists):
    """
    Used to queue bulk imports. It assigns a bulk import task to a specified import queue or a random one.
    If requested by the root user, the bulk import goes to the priority queue.

    :param to_import:
    :param import_queue:
    :param username:
    :param update_if_exists:
    :return: task
    """
    task_id=str(uuid.uuid4()) + '-' + username

    if username == 'root':
        queue_id = 'bulk_import_root'
        task_id += '-priority'
    elif import_queue:
        queue_id = 'bulk_import_' + str(hash(username + import_queue) % BULK_IMPORT_QUEUES_COUNT) #assing to one of 5 queues processed in order
        task_id += '-' + import_queue
    else:
        queue_id = 'bulk_import_' + str(random.randrange(0, BULK_IMPORT_QUEUES_COUNT)) #assing randomly to one of 5 queues processed in order
        task_id += '-default'

    task = bulk_import.apply_async((to_import, username, update_if_exists), task_id=task_id, queue=queue_id)
    return task

def parse_bulk_import_task_id(task_id):
    """
    Used to parse bulk import task id, which is in format '{uuid}-{username}-{queue}'.
    :param task_id:
    :return: dictionary with uuid, username, queue
    """
    task = { 'uuid': task_id[:37]}
    username = task_id[37:]
    queue_index = username.find('-')
    if queue_index != -1:
        queue = username[queue_index + 1:]
        username = username[:queue_index]
    else:
        queue = 'default'

    task['username'] = username
    task['queue'] = queue
    return task

def flower_get(url):
    """
    Returns a flower response from the given endpoint url.
    :param url:
    :return:
    """
    return requests.get('http://flower:5555/' + url, auth=HTTPBasicAuth(settings.FLOWER_USER, settings.FLOWER_PWD))

def task_exists(task_id):
    """
    This method is used to check Celery Task validity when state is PENDING. If task exists in
    Flower then it's considered as Valid task otherwise invalid task.
    """
    flower_response = flower_get('api/task/info/' + task_id)
    return flower_response and flower_response.status_code == 200 and flower_response.text


@celery.task(base=QueueOnce, bind=True)
def bulk_import(self, to_import, username, update_if_exists):
    from manage.imports.bulk_import import BulkImport
    return BulkImport().run_import(to_import, username, update_if_exists)

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


@celery.task(bind=True)
def add_references(self, SerializerClass, user, data, collection, host_url, cascade_mappings=False):
    from concepts.models import Concept
    from mappings.models import Mapping
    from concepts.views import ConceptVersionListView
    from mappings.views import MappingListView
    from collection.models import CollectionReferenceUtils

    collection.get_head().add_processing(self.request.id)

    expressions = data.get('expressions', [])
    concept_expressions = data.get('concepts', [])
    mapping_expressions = data.get('mappings', [])
    uri = data.get('uri')
    search_term = data.get('search_term', '')

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
        all_related_mappings = CollectionReferenceUtils.get_all_related_mappings(expressions, collection)
        expressions = expressions.union(all_related_mappings)

    added_references, errors = collection.add_references_in_bulk(expressions)

    update_collection_in_solr.delay(
        collection.get_head().id,
        added_references
    )

    collection.get_head().remove_processing(self.request.id)

    return added_references, errors


def index_resource(resource_ids, resource_klass, resource_version_klass, identifier):
    _resource_ids = resource_klass.objects.filter(id__in=resource_ids)
    resource_version_ids = list(set(resource_ids) - set(map(lambda m: m.id, _resource_ids)))
    version_ids = map(lambda r: r.get_latest_version.id, _resource_ids) + resource_version_ids
    kwargs = {}
    kwargs[identifier] = version_ids
    versions = resource_version_klass.objects.filter(**kwargs)
    update_all_in_index(resource_version_klass, versions)


@celery.task
def send_verify_email_message(name, email, verify_email_url, redirect_urls):
    return send_mail('[OCL] Verify your email address',
                     render_to_string(
                         "email/users/email_confirmation_message.txt",
                         context_instance=Context(
                             dict(name=name, verify_email_url=verify_email_url + "?" + redirect_urls)),
                     ),
                     settings.DEFAULT_FROM_EMAIL,
                     [email],
                     fail_silently=False,
                     )
