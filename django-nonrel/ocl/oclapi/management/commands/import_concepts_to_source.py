""" import_concepts_to_source - Command to import JSON lines concept file into OCL """
import json
import logging
from django.contrib.auth.models import User
from django.core.management import CommandError
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptDetailSerializer, ConceptVersionUpdateSerializer
from oclapi.management.commands import MockRequest, ImportCommand
from sources.models import SourceVersion

__author__ = 'misternando'
logger = logging.getLogger('batch')


class IllegalInputException(BaseException):
    pass


class InvalidStateException(BaseException):
    pass


class Command(ImportCommand):
    """ Command to import JSON lines concept file into OCL """
    help = 'Import concepts from a JSON file into a source'

    # Import Action Constants
    IMPORT_ACTION_NONE = 0
    IMPORT_ACTION_ADD = 1
    IMPORT_ACTION_UPDATE = 2
    IMPORT_ACTION_RETIRE = 3
    IMPORT_ACTION_DEACTIVATE = 4
    IMPORT_ACTION_SKIP = 5

    def do_import(self, user, source, input_file, options):
        """ Performs the import of JSON lines concept file into OCL """

        # Initialize counters
        cnt_skipped = 0
        cnt_no_diff = 0
        cnt_updated = 0
        cnt_inserted = 0
        cnt_retired = 0
        cnt_deactivated = 0

        logger.info('Import concepts to source...')

        # Retrieve latest source version and, if specified, create a new one
        self.source_version = SourceVersion.get_latest_version_of(source)
        if options['new_version']:
            try:
                new_version = SourceVersion.for_base_object(source, options['new_version'], previous_version=self.source_version)
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
            data = json.loads(line)
            cnt += 1
            # simple progress bar
            if (cnt % 10) == 0:
                self.stdout.write('%d of %d -- %d inserted, %d updated, %d retired, %d no diff, %d skipped with error, %d deactivated\n' % (cnt, total, cnt_inserted, cnt_updated, cnt_retired, cnt_no_diff, cnt_skipped, cnt_deactivated), ending='\r')
                self.stdout.flush()
            try:
                update_action = self.handle_concept(source, data)
                if update_action == self.IMPORT_ACTION_ADD:
                    cnt_inserted += 1
                elif update_action == self.IMPORT_ACTION_RETIRE:
                    cnt_retired += 1
                elif update_action == self.IMPORT_ACTION_UPDATE:
                    cnt_updated += 1
                elif update_action == self.IMPORT_ACTION_NONE:
                    cnt_no_diff += 1
            except IllegalInputException as exc:
                self.stderr.write('\n%s' % exc.message)
                self.stderr.write('\nFailed to parse line %s.  Skipping it...\n' % data)
                logger.warning('%s, failed to parse line %s.  Skipping it...' % (exc.message, data))
                cnt_skipped += 1
            except InvalidStateException as exc:
                self.stderr.write('\nSource is in an invalid state!')
                self.stderr.write('\n%s\n' % exc.message)
                logger.warning('Source is in an invalid state: %s' % exc.message)
                cnt_skipped += 1

        # Deactivate old records
        if options['deactivate_old_records']:
            self.stdout.write('\nDeactivating old concepts...\n')
            logger.info('Deactivating old concepts...')
            for version_id in self.concept_version_ids:
                try:
                    self.remove_concept_version(version_id)
                    cnt_deactivated += 1
                except InvalidStateException as exc:
                    self.stderr.write('Failed to inactivate concept! %s' % exc.message)
        else:
            self.stdout.write('\nSkipping deactivation loop...\n')
            logger.info('Skipping deactivation loop...')

        self.stdout.write('\nFinished importing concepts!\n')
        logger.info('Finished importing concepts!')
        self.stdout.write('Total concepts: %d -- %d inserted, %d updated, %d retired, %d no diff, %d skipped with error, %d deactivated\n' % (cnt, cnt_inserted, cnt_updated, cnt_retired, cnt_no_diff, cnt_skipped, cnt_deactivated))
        logger.info('Total concepts: %d -- %d inserted, %d updated, %d retired, %d no diff, %d skipped with error, %d deactivated\n' % (cnt, cnt_inserted, cnt_updated, cnt_retired, cnt_no_diff, cnt_skipped, cnt_deactivated))

    def handle_concept(self, source, data):
        """ Adds, updates, retires a single concept, or skips if no diff """
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')

        # Create new concept if doesn't already exist in OCLf
        try:
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)
        except Concept.DoesNotExist:
            self.add_concept(source, data)
            return self.IMPORT_ACTION_ADD

        # Get the corresponding concept version from OCL and update
        try:
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id, id__in=self.source_version.concepts)
        except ConceptVersion.DoesNotExist:
            raise InvalidStateException("Source %s has concept %s, but source version %s does not." %
                                        (source.mnemonic, concept.mnemonic, self.source_version.mnemonic))
        update_action = self.update_concept_version(concept_version, data)
        self.concept_version_ids.remove(concept_version.id)
        return update_action

    def add_concept(self, source, data):
        """ Adds a new concept """
        mnemonic = data['id']
        serializer = ConceptDetailSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new concept %s' % mnemonic)
        serializer.save(force_insert=True, parent_resource=source, child_list_attribute='concepts')
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new concept %s' % mnemonic)

    def update_concept_version(self, concept_version, data):
        """ Updates the concept, or skips if no diff. Retires if set. """
        clone = concept_version.clone()

        # Handle the special case of retiring a concept
        if 'retired' in data and clone.retired != data['retired']:
            concept = concept_version.versioned_object
            if data['retired']:
                errors = Concept.retire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to retire concept due to %s' % errors)
            else:
                errors = Concept.unretire(concept, self.user)
                if errors:
                    raise IllegalInputException('Failed to un-retire concept due to %s' % errors)

        # Generate the diff and update if different
        serializer = ConceptVersionUpdateSerializer(clone, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse concept to update: %s.' % concept_version.mnemonic)
        new_version = serializer.object
        diffs = ConceptVersion.diff(concept_version, new_version)
        if diffs:
            if 'names' in diffs:
                diffs['names'] = {'is': data.get('names')}
            if 'descriptions' in diffs:
                diffs['descriptions'] = {'is': data.get('descriptions')}
            clone.update_comment = json.dumps(diffs)
            serializer.save()
            if not serializer.is_valid():
                raise IllegalInputException('Could not persist update to concept: %s' % concept_version.mnemonic)
            return self.IMPORT_ACTION_UPDATE

        # No diff, so do nothing
        return self.IMPORT_ACTION_NONE

    def remove_concept_version(self, version_id):
        """ Deactivates a concept """
        # TODO: remove_concept_version actually inactivates, I thought it just retired the concept. This needs to change.
        try:
            version = ConceptVersion.objects.get(id=version_id)
            version.is_active = False
            version.save()
        except:
            raise InvalidStateException("Cannot delete concept version %s because it doesn't exist!" % version_id)
