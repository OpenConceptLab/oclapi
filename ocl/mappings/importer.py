""" Mappings importer module """
import json
import logging

import haystack
from datetime import datetime
from django.core.management import CommandError
from django.db.models import Q
from haystack.management.commands import update_index

from mappings.models import Mapping
from concepts.models import Concept
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer
from oclapi.management.commands import MockRequest, ImportActionHelper
from sources.models import Source, SourceVersion

from mappings.models import MappingVersion

__author__ = 'misternando,paynejd'
logger = logging.getLogger('batch')


class IllegalInputException(Exception):
    """ Exception for invalid JSON read from input file """
    pass


class InvalidStateException(Exception):
    """ Exception for invalid state of mapping within source """
    pass


class MappingsImporter(object):
    """ Class to import mappings """

    def __init__(self, source, mappings_file, output_stream, error_stream, user):
        """ Initialize mapping importer """
        self.source = source
        self.sources_cache = {}
        self.concepts_cache = {}
        self.mappings_file = mappings_file
        self.stdout = output_stream
        self.stderr = error_stream
        self.user = user
        self.count = 0
        self.test_mode = False
        self.action_count = {}

    def import_mappings(self, new_version=False, total=0, test_mode=False, deactivate_old_records=False, **kwargs):
        initial_signal_processor = haystack.signal_processor
        try:
            haystack.signal_processor = haystack.signals.BaseSignalProcessor
            import_start_time = datetime.now()
            logger.info('Started import at {}'.format(import_start_time.strftime("%Y-%m-%dT%H:%M:%S")))

            """ Main mapping importer loop """
            logger.info('Import mappings to source...')
            self.test_mode = test_mode

            # Retrieve latest source version and, if specified, create a new one
            self.source_version = SourceVersion.get_head_of(self.source)
            if new_version:
                try:
                    new_version = SourceVersion.for_base_object(
                        self.source, new_version, previous_version=self.source_version)
                    new_version.full_clean()
                    new_version.save()
                    new_version.seed_concepts()
                    new_version.seed_mappings()

                    self.source_version = new_version
                except Exception as exc:
                    raise CommandError('Failed to create new source version due to %s' % exc.args[0])

            # Load the JSON file line by line and import each line
            self.mapping_ids = set(self.source_version.get_mapping_ids())
            self.count = 0
            for line in self.mappings_file:

                # Load the next JSON line
                self.count += 1
                data = None
                try:
                    data = json.loads(line)
                except ValueError as exc:
                    str_log = 'Skipping invalid JSON line: %s. JSON: %s\n' % (exc.args[0], line)
                    self.stderr.write(str_log)
                    logger.warning(str_log)
                    self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

                # Process the import for the current JSON line
                if data:
                    try:
                        update_action = self.handle_mapping(data)
                        self.count_action(update_action)
                    except IllegalInputException as exc:
                        str_log = '%s, failed to parse line %s. Skipping it...\n' % (exc.args[0], data)
                        self.stderr.write(str_log)
                        logger.warning(str_log)
                        self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)
                    except InvalidStateException as exc:
                        str_log = 'Source is in an invalid state!\n%s\n%s\n' % (exc.args[0], data)
                        self.stderr.write(str_log)
                        logger.warning(str_log)
                        self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

                # Simple progress bars
                if (self.count % 10) == 0:
                    str_log = ImportActionHelper.get_progress_descriptor(
                        'mappings', self.count, total, self.action_count)
                    self.stdout.write(str_log, ending='\r')
                    self.stdout.flush()
                    if (self.count % 1000) == 0:
                        logger.info(str_log)

            # Done with the input file, so close it
            self.mappings_file.close()

            # Import complete - display final progress bar
            str_log = ImportActionHelper.get_progress_descriptor(
                'mappings', self.count, total, self.action_count)
            self.stdout.write(str_log, ending='\r')
            self.stdout.flush()
            logger.info(str_log)

            # Log remaining unhandled IDs
            str_log = 'Remaining %s unhandled mapping IDs\n' % len(self.mapping_ids)
            self.stdout.write(str_log)
            self.stdout.flush()
            logger.info(str_log)

            # Deactivate old records
            if deactivate_old_records:
                str_log = 'Deactivating old mappings...\n'
                self.stdout.write(str_log)
                logger.info(str_log)
                for mapping_id in self.mapping_ids:
                    try:
                        if self.remove_mapping(mapping_id):
                            self.count_action(ImportActionHelper.IMPORT_ACTION_DEACTIVATE)

                            # Log the mapping deactivation
                            str_log = 'Deactivated mapping: %s\n' % mapping_id
                            self.stdout.write(str_log)
                            logger.info(str_log)

                    except InvalidStateException as exc:
                        str_log = 'Failed to inactivate mapping on ID %s! %s\n' % (mapping_id, exc.args[0])
                        self.stderr.write(str_log)
                        logger.warning(str_log)
            else:
                str_log = 'Skipping deactivation loop...\n'
                self.stdout.write(str_log)
                logger.info(str_log)

            # Display final summary
            str_log = 'Finished importing mappings!\n'
            self.stdout.write(str_log)
            logger.info(str_log)
            str_log = ImportActionHelper.get_progress_descriptor(
                'mappings', self.count, total, self.action_count)
            self.stdout.write(str_log, ending='\r')
            logger.info(str_log)

            actions = self.action_count
            update_index_required = actions.get(ImportActionHelper.IMPORT_ACTION_ADD, 0) > 0
            update_index_required |= actions.get(ImportActionHelper.IMPORT_ACTION_UPDATE, 0) > 0

            if update_index_required:
                logger.info('Indexing objects updated since {}'.format(import_start_time.strftime("%Y-%m-%dT%H:%M:%S")))
                update_index.Command().handle(start_date=import_start_time.strftime("%Y-%m-%dT%H:%M:%S"), verbosity=2,
                                              workers=4, batchsize=100)
        finally:
            haystack.signal_processor = initial_signal_processor

    def handle_mapping(self, data):
        """ Handle importing of a single mapping """
        update_action = ImportActionHelper.IMPORT_ACTION_NONE

        # If mapping exists, update the mapping with the new data
        try:
            from_concept = self.get_concept(data['from_concept_url'])
            data['from_concept'] = from_concept
            query = Q(parent_id=self.source.id, map_type=data['map_type'],
                      from_concept_id=from_concept.id)
            if data.get('to_concept_url'):  # Internal mapping
                to_concept = self.get_concept(data['to_concept_url'])
                data['to_concept'] = to_concept
                query = query & Q(to_concept_id=to_concept.id)
            else:   # External mapping
                to_source = self.get_source(data['to_source_url'])
                data['to_source'] = to_source
                query = query & Q(to_source_id=to_source.id,
                                  to_concept_code=data['to_concept_code'],
                                  to_concept_name=data.get('to_concept_name'))

            # Perform the query - throws exception if does not exist
            mapping = Mapping.objects.get(query)

            # Mapping exists, but not in this source version
            mapping_version = MappingVersion.objects.get(versioned_object_id=mapping.id, is_latest_version=True)

            # Finish updating the mapping
            update_action = self.update_mapping(mapping, data)

            # Remove ID from the mapping list so that we know that mapping has been handled
            try:
                self.mapping_ids.remove(mapping_version.id)
            except KeyError:
                str_log = 'Key not found. Could not remove key %s from list of mapping IDs: %s\n' % (mapping.id, data)
                self.stderr.write(str_log)
                logger.warning(str_log)

            # Log the update
            if update_action:
                str_log = 'Updated mapping with ID %s: %s\n' % (mapping.id, data)
                self.stdout.write(str_log)
                logger.info(str_log)

        # Mapping does not exist, so create new one
        except Mapping.DoesNotExist:
            update_action = self.add_mapping(data)

            # Log the insert
            if update_action:
                str_log = 'Created new mapping: to - %s\n' % (data.get('to_concept_url') or (data.get('to_source_url') + ':' + data.get('to_concept_code')))
                self.stdout.write(str_log)
                logger.info(str_log)

        # Return the action performed
        return update_action

    def add_mapping(self, data):
        """ Create a new mapping """

        # Create the new mapping
        mapping = Mapping(**data)
        kwargs = {'parent_resource': self.source}
        if self.test_mode:
            mapping.save=lambda x: None
        
        errors = Mapping.persist_new(mapping, self.user, **kwargs)
        if errors:
            raise IllegalInputException(
                'Could not persist new mapping due to %s' % errors)

        return ImportActionHelper.IMPORT_ACTION_ADD

    def update_mapping(self, mapping, data):
        """ Update an existing mapping """

        # Generate the diff
        diffs = {}
        if 'retired' in data and mapping.retired != data['retired']:
            diffs['retired'] = {'was': mapping.retired, 'is': data['retired']}
        original = mapping.clone(self.user)
        serializer = MappingUpdateSerializer(
            mapping, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException(
                'Could not parse mapping to update mapping %s due to %s.' %
                (mapping.id, serializer.errors))
        mapping = serializer.object
        if 'retired' in diffs:
            mapping.retired = data['retired']
        diffs.update(Mapping.diff(original, mapping))

        # Update concept if different
        if diffs:
            if not self.test_mode:
                serializer.save()
                if not serializer.is_valid():
                    raise IllegalInputException(
                        'Could not persist update to mapping %s due to %s' %
                        (mapping.id, serializer.errors))

            return ImportActionHelper.IMPORT_ACTION_UPDATE

        # No diff, so do nothing
        return ImportActionHelper.IMPORT_ACTION_NONE

    def remove_mapping(self, mapping_id):
        """ Deactivates a mapping """
        try:
            mapping_version = MappingVersion.objects.get(id=mapping_id)
            mapping = Mapping.objects.get(id = mapping_version.versioned_object_id)
            if mapping.is_active:
                if not self.test_mode:
                    mapping.is_active = False
                    mapping.save()
                return ImportActionHelper.IMPORT_ACTION_DEACTIVATE
            else:
                return ImportActionHelper.IMPORT_ACTION_NONE
        except:
            raise InvalidStateException(
                "Cannot deactivate mapping %s because it doesn't exist!" % mapping_id)

    def count_action(self, update_action):
        """ Increments the counter for the specified action """
        if update_action in self.action_count:
            self.action_count[update_action] += 1
        else:
            self.action_count[update_action] = 1
    def get_concept(self, concept_url):
        result = self.concepts_cache.get(concept_url)
        if not result:
            result = Concept.objects.get(uri=concept_url)
            self.concepts_cache[concept_url] = result
        return result
    def get_source(self, source_url):
        result = self.sources_cache.get(source_url)
        if not result:
            result = Source.objects.get(uri=source_url)

            self.sources_cache[source_url] = result
        return result