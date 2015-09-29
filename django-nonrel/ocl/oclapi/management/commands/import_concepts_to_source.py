""" import_concepts_to_source - Command to import JSON lines concept file into OCL """
import json
import logging
from django.contrib.auth.models import User
from django.core.management import CommandError
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptDetailSerializer, ConceptVersionUpdateSerializer
from oclapi.management.commands import MockRequest, ImportCommand, ImportActionHelper
from sources.models import SourceVersion

__author__ = 'misternando,paynejd'
logger = logging.getLogger('batch')


class IllegalInputException(Exception):
    """ Exception for invalid JSON read from input file """
    pass


class InvalidStateException(Exception):
    """ Exception for invalid state of concept version within source """
    pass


class Command(ImportCommand):
    """ Command to import JSON lines concept file into OCL """
    help = 'Import concepts from a JSON file into a source'

    def do_import(self, user, source, input_file, options):
        """ Performs the import of JSON lines concept file into OCL """
        self.action_count = {}
        logger.info('Import concepts to source...')

        # Retrieve latest source version and, if specified, create a new one
        self.source_version = SourceVersion.get_latest_version_of(source)
        if options['new_version']:
            try:
                new_version = SourceVersion.for_base_object(
                    source, options['new_version'], previous_version=self.source_version)
                new_version.seed_concepts()
                new_version.seed_mappings()
                new_version.full_clean()
                new_version.save()
                self.source_version = new_version
            except Exception as exc:
                raise CommandError('Failed to create new source version due to %s' % exc.args[0])

        # Load the JSON file line by line and import each line
        total = options.get('total', '(Unknown)')
        self.user = User.objects.filter(is_superuser=True)[0]
        self.concept_version_ids = set(self.source_version.concepts)
        cnt = 0
        for line in input_file:

            # Load the next JSON line
            cnt += 1
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
                    update_action = self.handle_concept(source, data)
                    self.count_action(update_action)
                except IllegalInputException as exc:
                    str_log = '\n%s\nFailed to parse line: %s. Skipping it...\n' % (exc.args[0], data)
                    self.stderr.write(str_log)
                    logger.warning(str_log)
                    self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)
                except InvalidStateException as exc:
                    str_log = '\nSource is in an invalid state!\n%s\n' % exc.args[0]
                    self.stderr.write(str_log)
                    logger.warning(str_log)
                    self.count_action(ImportActionHelper.IMPORT_ACTION_SKIP)

            # Simple progress bar
            if (cnt % 10) == 0:
                str_log = ImportActionHelper.get_progress_descriptor(cnt, total, self.action_count)
                self.stdout.write(str_log, ending='\r')
                self.stdout.flush()
                if (cnt % 1000) == 0:
                    logger.info(str_log)

        # Done with the input file, so close it
        input_file.close()

        # Import complete - display final progress bar
        str_log = ImportActionHelper.get_progress_descriptor(cnt, total, self.action_count)
        self.stdout.write(str_log, ending='\r')
        self.stdout.flush()
        logger.info(str_log)

        # Log remaining unhandled IDs
        self.stdout.write('\nRemaining unhandled concept versions:\n', ending='\r')
        self.stdout.write(','.join(str(el) for el in self.concept_version_ids), ending='\r')
        self.stdout.flush()
        logger.info('Remaining unhandled concept versions:')
        logger.info(','.join(str(el) for el in self.concept_version_ids))

        # Deactivate old records
        if options['deactivate_old_records']:
            self.stdout.write('\nDeactivating old concepts...\n')
            logger.info('Deactivating old concepts...')
            for version_id in self.concept_version_ids:
                try:
                    if self.remove_concept_version(version_id):
                        self.count_action(ImportActionHelper.IMPORT_ACTION_DEACTIVATE)

                        # Log the mapping deactivation
                        str_log = '\nDeactivated concept version: %s\n' % version_id
                        self.stdout.write(str_log)
                        logger.info(str_log)

                except InvalidStateException as exc:
                    self.stderr.write('Failed to inactivate concept! %s' % exc.args[0])
        else:
            str_log = '\nSkipping deactivation loop...\n'
            self.stdout.write(str_log)
            logger.info(str_log)

        # Display final summary
        self.stdout.write('\nFinished importing concepts!\n')
        logger.info('Finished importing concepts!')
        str_log = ImportActionHelper.get_progress_descriptor(cnt, total, self.action_count)
        self.stdout.write(str_log, ending='\r')
        logger.info(str_log)

    def handle_concept(self, source, data):
        """ Adds, updates, retires/unretires a single concept, or skips if no diff """
        update_action = retire_action = ImportActionHelper.IMPORT_ACTION_NONE

        # Ensure mnemonic included in data
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')

        # If concept exists, update the concept with the new data (ignoring retired status for now)
        try:
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id,
                                                         id__in=self.source_version.concepts)
            update_action = self.update_concept_version(concept_version, data)

            # Remove ID from the concept version list so that we know concept has been handled
            self.concept_version_ids.remove(concept_version.id)

            # Log the update
            if update_action:
                str_log = '\nUpdated concept: %s\n' % data
                self.stdout.write(str_log)
                logger.info(str_log)

        # Concept does not exist in OCL, so create new one
        except Concept.DoesNotExist:
            update_action = self.add_concept(source, data)

            # Log the insert
            if update_action:
                str_log = '\nCreated new concept: %s\n' % data
                self.stdout.write(str_log)
                logger.info(str_log)

            # Reload the concept so that the retire/unretire step will work
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)

        # Concept exists, but not in this source version
        except ConceptVersion.DoesNotExist:
            raise InvalidStateException(
                "Source %s has concept %s, but source version %s does not." %
                (source.mnemonic, concept.mnemonic, self.source_version.mnemonic))

        # Handle retired status - if different, will create an additional concept version
        if 'retired' in data:
            retire_action = self.update_concept_retired_status(concept, data['retired'])
            if retire_action == ImportActionHelper.IMPORT_ACTION_RETIRE:
                str_log = '\nRetired concept: %s\n' % data
                self.stdout.write(str_log)
                logger.info(str_log)
            elif retire_action == ImportActionHelper.IMPORT_ACTION_UNRETIRE:
                str_log = '\nUn-retired concept: %s\n' % data
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
                raise IllegalInputException('Could not persist new concept %s' % data['id'])
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
                    raise IllegalInputException(
                        'Could not persist update to concept: %s' % concept_version.mnemonic)
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
        try:
            version = ConceptVersion.objects.get(id=version_id)
            if version.is_active:
                if not self.test_mode:
                    version.is_active = False
                    version.save()
                return ImportActionHelper.IMPORT_ACTION_DEACTIVATE
            else:
                return ImportActionHelper.IMPORT_ACTION_NONE
        except:
            raise InvalidStateException(
                "Cannot deactivate concept version %s because it doesn't exist!" % version_id)

    def count_action(self, update_action):
        """ Increments the counter for the specified action """
        if update_action in self.action_count:
            self.action_count[update_action] += 1
        else:
            self.action_count[update_action] = 1
