""" Mappings importer module """
import json
import logging
from django.core.management import CommandError
from django.db.models import Q
from mappings.models import Mapping
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer
from oclapi.management.commands import MockRequest, ImportActionHelper
from sources.models import SourceVersion

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
        self.mappings_file = mappings_file
        self.stdout = output_stream
        self.stderr = error_stream
        self.user = user
        self.count = 0
        self.test_mode = False
        self.action_count = {}

    def import_mappings(self, new_version=False, total=0, test_mode=False, **kwargs):
        """ Main mapping importer loop """
        logger.info('Import mappings to source...')
        self.test_mode = test_mode

        # Retrieve latest source version and, if specified, create a new one
        self.source_version = SourceVersion.get_latest_version_of(self.source)
        if new_version:
            try:
                new_version = SourceVersion.for_base_object(
                    self.source, new_version, previous_version=self.source_version)
                new_version.seed_concepts()
                new_version.seed_mappings()
                new_version.full_clean()
                new_version.save()
                self.source_version = new_version
            except Exception as exc:
                raise CommandError('Failed to create new source version due to %s' % exc.args[0])

        # Load the JSON file line by line and import each line
        self.mapping_ids = set(self.source_version.mappings)
        self.count = 0
        for line in self.mappings_file:

            # Load the next JSON line
            self.count += 1
            data = None
            try:
                data = json.loads(line)
            except ValueError as exc:
                str_log = '\nSkipping invalid JSON line: %s. JSON: %s' % (exc.args[0], line)
                self.stderr.write(str_log)
                logger.warning(str_log)
                self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

            # Process the import for the current JSON line
            if data:
                try:
                    update_action = self.handle_mapping(data)
                    self.count_action(update_action)
                except IllegalInputException as exc:
                    str_log = '\n%s, failed to parse line %s. Skipping it...\n' % (exc.args[0], data)
                    self.stderr.write(str_log)
                    logger.warning(str_log)
                    self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)
                except InvalidStateException as exc:
                    str_log = '\nSource is in an invalid state!\n%s\n%s\n' % (exc.args[0], data)
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
        str_log = '\nRemaining unhandled mapping IDs:\n'
        self.stdout.write(str_log, ending='\r')
        logger.info(str_log)
        str_log = ','.join(str(el) for el in self.mapping_ids)
        self.stdout.write(str_log, ending='\r')
        self.stdout.flush()
        logger.info(str_log)

        # Deactivate old records
        if kwargs['deactivate_old_records']:
            str_log = '\nDeactivating old mappings...\n'
            self.stdout.write(str_log)
            logger.info(str_log)
            for mapping_id in self.mapping_ids:
                try:
                    if self.remove_mapping(mapping_id):
                        self.count_action(ImportActionHelper.IMPORT_ACTION_DEACTIVATE)

                        # Log the mapping deactivation
                        str_log = '\nDeactivated mapping: %s\n' % mapping_id
                        self.stdout.write(str_log)
                        logger.info(str_log)

                except InvalidStateException as exc:
                    str_log = 'Failed to inactivate mapping on ID %s! %s' % (mapping_id, exc.args[0])
                    self.stderr.write(str_log)
                    logger.warning(str_log)
        else:
            str_log = '\nSkipping deactivation loop...\n'
            self.stdout.write(str_log)
            logger.info(str_log)

        # Display final summary
        str_log = '\nFinished importing mappings!\n'
        self.stdout.write(str_log)
        logger.info(str_log)
        str_log = ImportActionHelper.get_progress_descriptor(
            'mappings', self.count, total, self.action_count)
        self.stdout.write(str_log, ending='\r')
        logger.info(str_log)

    def handle_mapping(self, data):
        """ Handle importing of a single mapping """
        update_action = ImportActionHelper.IMPORT_ACTION_NONE

        # Parse the mapping JSON to ensure that it is a valid mapping (not just valid JSON)
        serializer = MappingCreateSerializer(
            data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException(
                'Could not parse mapping %s due to %s' % (data, serializer.errors))

        # If mapping exists, update the mapping with the new data
        try:
            # Build the query
            mapping = serializer.save(commit=False)
            query = Q(parent_id=self.source.id, map_type=mapping.map_type,
                      from_concept=mapping.from_concept)
            if mapping.to_concept:  # Internal mapping
                query = query & Q(to_concept=mapping.to_concept)
            else:   # External mapping
                query = query & Q(to_source_id=mapping.to_source.id,
                                  to_concept_code=mapping.to_concept_code,
                                  to_concept_name=mapping.to_concept_name)

            # Perform the query - throws exception if does not exist
            mapping = Mapping.objects.get(query)

            # Mapping exists, but not in this source version
            if mapping.id not in self.source_version.mappings:
                raise InvalidStateException(
                    "Source %s has mapping %s, but source version %s does not. Mapping not updated." %
                    (self.source.mnemonic, mapping.id, self.source_version.mnemonic))

            # Finish updating the mapping
            update_action = self.update_mapping(mapping, data)

            # Remove ID from the mapping list so that we know that mapping has been handled
            try:
                self.mapping_ids.remove(mapping.id)
            except KeyError:
                str_log = '\nKey not found. Could not remove key %s from list of mapping IDs: %s\n' % (mapping.id, data)
                self.stderr.write(str_log)
                logger.warning(str_log)

            # Log the update
            if update_action:
                str_log = '\nUpdated mapping with ID %s: %s\n' % (mapping.id, data)
                self.stdout.write(str_log)
                logger.info(str_log)

        # Mapping does not exist, so create new one
        except Mapping.DoesNotExist:
            update_action = self.add_mapping(data)

            # Log the insert
            if update_action:
                str_log = '\nCreated new mapping: %s\n' % data
                self.stdout.write(str_log)
                logger.info(str_log)

        # Return the action performed
        return update_action

    def add_mapping(self, data):
        """ Create a new mapping """

        # Create the new mapping
        serializer = MappingCreateSerializer(
            data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException(
                'Could not persist new mapping due to %s' % serializer.errors)
        if not self.test_mode:
            serializer.save(force_insert=True, parent_resource=self.source)
            if not serializer.is_valid():
                raise IllegalInputException(
                    'Could not persist new mapping due to %s' % serializer.errors)

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
            mapping = Mapping.objects.get(id=mapping_id)
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
