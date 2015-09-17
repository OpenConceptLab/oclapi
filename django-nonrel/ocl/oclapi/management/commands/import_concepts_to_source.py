""" import_concepts_to_source - Command to import JSON lines concept file into OCL """
import json
import logging
from django.contrib.auth.models import User
from django.core.management import CommandError
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptDetailSerializer, ConceptVersionUpdateSerializer
from oclapi.management.commands import MockRequest, ImportCommand
from sources.models import SourceVersion

__author__ = 'misternando,paynejd'
logger = logging.getLogger('batch')


class IllegalInputException(BaseException):
    """ Exception for invalid JSON read from input file """
    pass


class InvalidStateException(BaseException):
    """ Exception for invalid state of concept version within source """
    pass


class Command(ImportCommand):
    """ Command to import JSON lines concept file into OCL """
    help = 'Import concepts from a JSON file into a source'

    # Import Action Constants - can be combined if multiple actions performed on a concept
    IMPORT_ACTION_NONE = 0
    IMPORT_ACTION_ADD = 0b1  # 1
    IMPORT_ACTION_UPDATE = 0b10  # 2
    IMPORT_ACTION_RETIRE = 0b100  # 4
    IMPORT_ACTION_UNRETIRE = 0b1000  # 8
    IMPORT_ACTION_DEACTIVATE = 0b10000  # 16
    IMPORT_ACTION_SKIP = 0b100000  # 32

    IMPORT_ACTION_NAMES = {
        IMPORT_ACTION_NONE: 'no action/no diff',
        IMPORT_ACTION_ADD: 'added',
        IMPORT_ACTION_UPDATE: 'updated',
        IMPORT_ACTION_RETIRE: 'retired',
        IMPORT_ACTION_UNRETIRE: 'unretired',
        IMPORT_ACTION_DEACTIVATE: 'deactivated',
        IMPORT_ACTION_SKIP: 'skipped due to error',
    }

    ORDERED_ACTION_LIST = [32, 16, 8, 4, 2, 1]


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
                raise CommandError('Failed to create new source version due to %s' % exc.message)

        # Load the JSON file line by line and import each line as a concept
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
                self.stderr.write('\n%s' % exc.message)
                self.stderr.write('\nInvalid JSON line: %s. Skipping it...\n' % line)
                logger.warning('%s, invalid JSON line: %s. Skipping it...' % (exc.message, line))
                self.count_action(self.IMPORT_ACTION_SKIP)

            # Process the import for the current JSON line
            if data:
                try:
                    update_action = self.handle_concept(source, data)
                    self.count_action(update_action)
                except IllegalInputException as exc:
                    self.stderr.write('\n%s' % exc.message)
                    self.stderr.write('\nFailed to parse line %s. Skipping it...\n' % data)
                    logger.warning(
                        '%s, failed to parse line %s. Skipping it...' % (exc.message, data))
                    self.count_action(self.IMPORT_ACTION_SKIP)
                except InvalidStateException as exc:
                    self.stderr.write('\nSource is in an invalid state!\n%s\n' % exc.message)
                    logger.warning('Source is in an invalid state: %s' % exc.message)
                    self.count_action(self.IMPORT_ACTION_SKIP)
            else:
                self.stderr.write('\nEmpty JSON line, skipping it...\n%s\n' % line)
                logger.info('Empty JSON line, skipping it... %s' % line)
                self.count_action(self.IMPORT_ACTION_SKIP)

            # Simple progress bar
            if (cnt % 10) == 0:
                self.stdout.write(
                    self.get_progress_descriptor(cnt, total, self.action_count), ending='\r')
                self.stdout.flush()

        # Deactivate old records
        if options['deactivate_old_records']:
            self.stdout.write('\nDeactivating old concepts...\n')
            logger.info('Deactivating old concepts...')
            for version_id in self.concept_version_ids:
                try:
                    self.remove_concept_version(version_id)
                    self.count_action(self.IMPORT_ACTION_DEACTIVATE)
                except InvalidStateException as exc:
                    self.stderr.write('Failed to inactivate concept! %s' % exc.message)
        else:
            self.stdout.write('\nSkipping deactivation loop...\n')
            logger.info('Skipping deactivation loop...')

        self.stdout.write('\nFinished importing concepts!\n')
        logger.info('Finished importing concepts!')
        self.stdout.write(self.get_progress_descriptor(cnt, total, self.action_count))
        logger.info(self.get_progress_descriptor(cnt, total, self.action_count))

    def handle_concept(self, source, data):
        """ Adds, updates, retires/unretires a single concept, or skips if no diff """
        update_action = retire_action = self.IMPORT_ACTION_NONE

        # Ensure mnemonic included in data
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')

        # Update the concept with the new data, ignoring retired status until next step
        # TODO: This does not ignore retired status -- instead it modifies the field without
        # actually modifying the retired status
        try:
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id,
                                                         id__in=self.source_version.concepts)
            update_action = self.update_concept_version(concept_version, data)

            # Remove id from the concept version list so that we know concept has been handled
            self.concept_version_ids.remove(concept_version.id)

        # Concept does not exist in OCL, so create new one
        except Concept.DoesNotExist:
            update_action = self.add_concept(source, data)
            # Load the concept so that the retire/unretire step will work
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)

        # Concept exists, but not in this source version
        except ConceptVersion.DoesNotExist:
            raise InvalidStateException(
                "Source %s has concept %s, but source version %s does not." %
                (source.mnemonic, concept.mnemonic, self.source_version.mnemonic))

        # Handle retired status - if different, will create an additional concept version
        if 'retired' in data:
            retire_action = self.update_concept_retired_status(concept, data['retired'])

        # Return the list of actions performed
        return update_action + retire_action

    def add_concept(self, source, data):
        """ Adds a new concept """
        mnemonic = data['id']
        self.stdout.write('Adding new concept: %s' % data)
        serializer = ConceptDetailSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new concept %s' % mnemonic)
        if not self.test_mode:
            serializer.save(
                force_insert=True, parent_resource=source, child_list_attribute='concepts')
            if not serializer.is_valid():
                raise IllegalInputException('Could not persist new concept %s' % mnemonic)
        return self.IMPORT_ACTION_ADD

    def update_concept_version(self, concept_version, data):
        """ Updates the concept, or skips if no diff. Ignores retired status. """
        # TODO: update_concept_version must ignore retired status

        # Generate the diff and update if different
        clone = concept_version.clone()
        serializer = ConceptVersionUpdateSerializer(
            clone, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException(
                'Could not parse concept to update: %s.' % concept_version.mnemonic)
        new_version = serializer.object
        diffs = ConceptVersion.diff(concept_version, new_version)
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
            return self.IMPORT_ACTION_UPDATE

        # No diff, so do nothing
        return self.IMPORT_ACTION_NONE

    def update_concept_retired_status(self, concept, new_retired_state):
        """ Updates and persists a new retired status for a concept """

        # Do nothing if retired status is unchanged
        concept_version = ConceptVersion.get_latest_version_of(concept)
        if concept_version.retired == new_retired_state:
            return self.IMPORT_ACTION_NONE

        # Retire/un-retire the concept
        if new_retired_state:
            if not self.test_mode:
                errors = Concept.retire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to retire concept due to %s' % errors)
            return self.IMPORT_ACTION_RETIRE
        else:
            if not self.test_mode:
                errors = Concept.unretire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to un-retire concept due to %s' % errors)
            return self.IMPORT_ACTION_UNRETIRE

    def remove_concept_version(self, version_id):
        """ Deactivates a concept """
        try:
            version = ConceptVersion.objects.get(id=version_id)
            if not self.test_mode:
                version.is_active = False
                version.save()
        except:
            raise InvalidStateException(
                "Cannot delete concept version %s because it doesn't exist!" % version_id)
        return self.IMPORT_ACTION_DEACTIVATE

    def get_action_string(self, combined_action_value):
        """
        Returns text name of the action, where action is an integer of one or
        more of the import actions added together.
        E.g. if action = 8 + 2, returns "updated + unretired"
        """
        if combined_action_value in self.IMPORT_ACTION_NAMES:
            return self.IMPORT_ACTION_NAMES[combined_action_value]
        combined_action_text = ''
        for individual_action_value in self.ORDERED_ACTION_LIST:
            if combined_action_value >= individual_action_value:
                if combined_action_text:
                    combined_action_text += (
                        ' + ' + self.IMPORT_ACTION_NAMES[individual_action_value])
                else:
                    combined_action_text = self.IMPORT_ACTION_NAMES[individual_action_value]
                combined_action_value -= individual_action_value
        return combined_action_text

    def get_progress_descriptor(self, current_num, total_num, action_count):
        """ Returns a string with the current counts of the import process """
        str_descriptor = '%d of %d -' % (current_num, total_num)
        for action_value, num in action_count.items():
            str_descriptor += ' %d %s,' % (num, self.get_action_string(action_value))
        str_descriptor += '\n'
        return str_descriptor

    def count_action(self, update_action):
        """ Increments the counter for the specified action """
        if update_action in self.action_count:
            self.action_count[update_action] += 1
        else:
            self.action_count[update_action] = 1
