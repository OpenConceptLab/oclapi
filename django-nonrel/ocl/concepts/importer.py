""" Concepts importer module """
from datetime import datetime
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import CommandError
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptDetailSerializer, ConceptVersionUpdateSerializer
from oclapi.management.commands import MockRequest, ImportActionHelper
from sources.models import SourceVersion
import json
import logging

__author__ = 'misternando,paynejd'
logger = logging.getLogger('batch')


class IllegalInputException(Exception):
    """ Exception for invalid JSON read from input file """
    pass


class InvalidStateException(Exception):
    """ Exception for invalid state of concept version within source """
    pass


class ValidationLogger:
    def __init__(self, output_file_name='bulk_import_validation_errors_%s.csv' % datetime.now().strftime('%Y%m%d%H%M%S'), output=None):
        self.count = 0
        self.output = output
        self.output_file_name = output_file_name

    def append_concept(self, data, errors):
        if self.count is 0:
            self.init_output()
            self.output.write("MNEMONIC,ERROR,JSON\n")

        self.count += 1

        for error in errors:
            csv_line = "%s,%s,%s\n" % (data['id'], error, data)
            self.output.write(csv_line)

    def init_output(self):
        if self.output is None:
            self.output = open(self.output_file_name, 'w+')

    def close(self):
        self.output.flush()
        self.output.close()


class ConceptsImporter(object):
    def __init__(self, source, concepts_file, user, output_stream, error_stream, save_validation_errors=True, validation_logger=None):
        """ Initialize mapping importer """
        self.source = source
        self.concepts_file = concepts_file
        self.stdout = output_stream
        self.stderr = error_stream
        self.user = user
        # Retrieve latest source version and, if specified, create a new one
        self.source_version = SourceVersion.get_latest_version_of(self.source)
        self.validation_logger = validation_logger
        self.save_validation_errors = save_validation_errors

        if self.save_validation_errors and self.validation_logger is None:
            self.validation_logger = ValidationLogger()

    def info(self, message, ending='', flush=False):
        self.stdout.write(message, ending)
        logger.info(message)
        if flush:
            self.stdout.flush()

    def error(self, error, ending='', flush=False):
        self.stderr.write(error, ending)
        logger.warning(error)
        if flush:
            self.stderr.flush()

    def import_concepts(self, new_version=False, total=0, test_mode=False, deactivate_old_records=False, **kwargs):
        self.action_count = {}
        self.test_mode = test_mode
        self.info('Import concepts to source...')
        self.handle_new_source_version(new_version)

        # Load the JSON file line by line and import each line
        self.user = User.objects.filter(is_superuser=True)[0]
        self.concept_version_ids = set(self.source_version.concepts)

        self.create_concept_versions_map()

        lines_handled = self.handle_lines_in_input_file(total)
        self.output_unhandled_concept_version_ids()
        self.handle_deactivation__of_old_records(deactivate_old_records)  # Display final summary
        self.output_summary(lines_handled, total)

    def output_unhandled_concept_version_ids(self):
        # Log remaining unhandled IDs
        self.info('Remaining unhandled concept versions:\n', ending='\r')

        log = ','.join(str(el) for el in self.concept_version_ids)
        self.info(log, ending='\r', flush=True)

    def handle_new_source_version(self, new_version):
        if not new_version:
            return
        try:
            self.create_new_source_version(new_version)
        except Exception as exc:
            raise CommandError('Failed to create new source version due to %s' % exc.args[0])

    def output_summary(self, lines_handled, total='Unknown'):
        self.info('Finished importing concepts!\n')

        log = ImportActionHelper.get_progress_descriptor(
            'concepts', lines_handled, total, self.action_count)
        self.info(log)

    def handle_deactivation__of_old_records(self, deactivate_old_records):
        # Deactivate old records
        if not deactivate_old_records:
            self.info('Skipping deactivation loop...\n')
            return

        self.info('Deactivating old concepts...\n')

        for version_id in self.concept_version_ids:
            try:
                self.remove_concept_version(version_id)
                self.count_action(ImportActionHelper.IMPORT_ACTION_DEACTIVATE)

                # Log the mapping deactivation
                self.info('Deactivated concept version: %s\n' % version_id)

            except InvalidStateException as exc:
                self.error('Failed to inactivate concept version on ID %s! %s\n' % (version_id, exc.args[0]))

    def handle_lines_in_input_file(self, total):
        lines_handled = 0
        for line in self.concepts_file:
            # Load the next JSON line
            lines_handled += 1
            data = self.json_to_concept(line)  # Process the import for the current JSON line
            self.try_import_concept(data)

            # Simple progress bar
            if (lines_handled % 10) == 0:
                log = ImportActionHelper.get_progress_descriptor(
                    'concepts', lines_handled, total, self.action_count)
                self.stdout.write(log, ending='\r')
                self.stdout.flush()
                if (lines_handled % 1000) == 0:
                    logger.info(log)

        # Done with the input file, so close it
        self.concepts_file.close()
        if self.validation_logger:
            self.validation_logger.close()
        # Import complete - display final progress bar
        log = ImportActionHelper.get_progress_descriptor(
            'concepts', lines_handled, total, self.action_count)
        self.info(log, ending='\r', flush=True)
        return lines_handled

    def try_import_concept(self, data):
        if not data:
            return
        try:
            update_action = self.handle_concept(self.source, data)
            self.count_action(update_action)
        except IllegalInputException as exc:
            exc_message = '%s\nFailed to parse line: %s. Skipping it...\n' % (exc.args[0], data)
            self.handle_exception(exc_message)
        except InvalidStateException as exc:
            exc_message = 'Source is in an invalid state!\n%s\n%s\n' % (exc.args[0], data)
            self.handle_exception(exc_message)
        except ValidationError as exc:
            if self.save_validation_errors:
                self.validation_logger.append_concept(data, exc.messages)

            exc_message = '%s\nValidation failed: %s. Skipping it...\n' % (''.join(exc.messages), data)
            self.handle_exception(exc_message)
        except Exception as exc:
            exc_message = '%s\nSomething unexpected occured: %s. Skipping it...\n' % (exc.message, data)
            self.handle_exception(exc_message)

    def json_to_concept(self, line):
        data = None
        try:
            data = json.loads(line)
        except ValueError as exc:
            self.error('Skipping invalid JSON line: %s. JSON: %s\n' % (exc.args[0], line))
            self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

        return data

    def handle_exception(self, exception_message):
        self.error(exception_message)
        self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

    def create_new_source_version(self, new_version):
        new_source_version = SourceVersion.for_base_object(
            self.source, new_version, previous_version=self.source_version)
        new_source_version.seed_concepts()
        new_source_version.seed_mappings()
        new_source_version.full_clean()
        new_source_version.save()
        self.source_version = new_source_version

    def handle_concept(self, source, data):
        """ Adds, updates, retires/unretires a single concept, or skips if no diff """
        update_action = retire_action = ImportActionHelper.IMPORT_ACTION_NONE

        # Ensure mnemonic included in data
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')
        concept_name = data['concept_class']
        # If concept exists, update the concept with the new data (ignoring retired status for now)
        try:
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)
            concept_version = ConceptVersion.objects.get(id=self.concepts_versions_map[concept.id])

            update_action = self.update_concept_version(concept_version, data)

            # Remove ID from the concept version list so that we know concept has been handled
            if concept_version.id not in self.concept_version_ids:
                self.error('Key not found. Could not remove key %s from list of concept version IDs: %s\n' % (concept_version.id, data))
            else:
                self.concept_version_ids.remove(concept_version.id)

            # Log the update
            if update_action:
                self.info('Updated concept, replacing version ID %s: %s\n' % (concept_version.id, data))

        # Concept does not exist in OCL, so create new one
        except Concept.DoesNotExist:
            update_action = self.add_concept(source, data)

            # Log the insert
            if update_action:
                self.info('Created new concept: %s = %s\n' % (mnemonic, concept_name))

            # Reload the concept so that the retire/unretire step will work
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)

        # Concept exists, but not in this source version
        except (ConceptVersion.DoesNotExist, KeyError):
            raise InvalidStateException(
                "Source %s has concept %s, but source version %s does not." %
                (source.mnemonic, concept.mnemonic, self.source_version.mnemonic))

        # Handle retired status - if different, will create an additional concept version
        if 'retired' in data:
            retire_action = self.update_concept_retired_status(concept, data['retired'])
            if retire_action == ImportActionHelper.IMPORT_ACTION_RETIRE:
                str_log = 'Retired concept: %s = %s\n' % (mnemonic, concept_name)
                self.stdout.write(str_log)
                logger.info(str_log)
            elif retire_action == ImportActionHelper.IMPORT_ACTION_UNRETIRE:
                str_log = 'Un-retired concept: %s = %s\n' % (mnemonic, concept_name)
                self.stdout.write(str_log)
                logger.info(str_log)

        # Return the list of actions performed
        return update_action + retire_action

    def add_concept(self, source, data):
        """ Adds a new concept -- NOTE: data['id'] is the concept mnemonic """
        serializer = ConceptDetailSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new concept %s' % data['id'])
        if not self.test_mode:
            serializer.save(force_insert=True, parent_resource=source, child_list_attribute='concepts')
            if not serializer.is_valid():
                raise ValidationError(serializer.errors)
        return ImportActionHelper.IMPORT_ACTION_ADD

    def update_concept_version(self, concept_version, data):
        """ Updates the concept, or skips if no diff. Ignores retired status. """

        # Generate the diff
        clone = concept_version.clone()
        serializer = ConceptVersionUpdateSerializer(
            clone, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException(
                'Could not parse concept to update: %s.' % concept_version.mnemonic)
        new_version = serializer.object
        diffs = ConceptVersion.diff(concept_version, new_version)

        # Update concept if different
        if diffs:
            if 'names' in diffs:
                diffs['names'] = {'is': data.get('names')}
            if 'descriptions' in diffs:
                diffs['descriptions'] = {'is': data.get('descriptions')}
            clone.update_comment = json.dumps(diffs)
            if not self.test_mode:
                serializer.save()
                if not serializer.is_valid():
                    raise ValidationError(serializer.errors)
            return ImportActionHelper.IMPORT_ACTION_UPDATE

        # No diff, so do nothing
        return ImportActionHelper.IMPORT_ACTION_NONE

    def update_concept_retired_status(self, concept, new_retired_state):
        """ Updates and persists a new retired status for a concept """

        # Do nothing if retired status is unchanged
        concept_version = ConceptVersion.get_latest_version_of(concept)
        if concept_version.retired == new_retired_state:
            return ImportActionHelper.IMPORT_ACTION_NONE

        # Retire/un-retire the concept
        if new_retired_state:
            if not self.test_mode:
                errors = Concept.retire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to retire concept due to %s' % errors)
            return ImportActionHelper.IMPORT_ACTION_RETIRE
        else:
            if not self.test_mode:
                errors = Concept.unretire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to un-retire concept due to %s' % errors)
            return ImportActionHelper.IMPORT_ACTION_UNRETIRE

    def remove_concept_version(self, version_id):
        """ Deactivates a concept """
        version_query = ConceptVersion.objects.filter(id=version_id)

        if version_query.count() is 0:
            raise InvalidStateException(
                "Cannot deactivate concept version %s because it doesn't exist!" % version_id)

        version = version_query.get()
        if not version.is_active:
            return ImportActionHelper.IMPORT_ACTION_NONE

        if not self.test_mode:
            version.is_active = False
            version.save()

        return ImportActionHelper.IMPORT_ACTION_DEACTIVATE

    def count_action(self, update_action):
        """ Increments the counter for the specified action """
        if update_action not in self.action_count:
            self.action_count[update_action] = 0

        self.action_count[update_action] += 1

    def create_concept_versions_map(self):
        # Create map for all concept ids to concept versions
        try:
            versions_list = ConceptVersion.objects.values('id', 'versioned_object_id').filter(
                id__in=self.concept_version_ids)
            self.concepts_versions_map = dict((x['versioned_object_id'], x['id']) for x in versions_list)
        except KeyError:
            raise InvalidStateException("Map couldn't be created, possible corruption of data")
