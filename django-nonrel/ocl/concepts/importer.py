""" Concepts importer module """
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

class ConceptsImporter(object):
  def __init__(self, source, concepts_file, user, output_stream, error_stream):
    """ Initialize mapping importer """
    self.source = source
    self.concepts_file = concepts_file
    self.stdout = output_stream
    self.stderr = error_stream
    self.user = user
    # Retrieve latest source version and, if specified, create a new one
    self.source_version = SourceVersion.get_latest_version_of(self.source)
    

  def import_concepts(self, new_version=False, total=0, test_mode=False, deactivate_old_records=False, **kwargs):
    self.action_count = {}
    self.test_mode = test_mode
    logger.info('Import concepts to source...')
    if new_version:
      try:
        self.create_new_source_version(new_version)
      except Exception as exc:
        raise CommandError('Failed to create new source version due to %s' % exc.args[0])

    # Load the JSON file line by line and import each line
    total = total or '(Unknown)'
    self.user = User.objects.filter(is_superuser=True)[0]
    self.concept_version_ids = set(self.source_version.concepts)
    cnt = 0

    self.create_concept_versions_map()

    for line in self.concepts_file:

        # Load the next JSON line
        cnt += 1
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
                update_action = self.handle_concept(self.source, data)
                self.count_action(update_action)
            except IllegalInputException as exc:
                exc_message = '%s\nFailed to parse line: %s. Skipping it...\n' % (exc.args[0], data)
                self.handle_exception(exc_message)
            except InvalidStateException as exc:
                exc_message = 'Source is in an invalid state!\n%s\n%s\n' % (exc.args[0], data)
                self.handle_exception(exc_message)
            except ValidationError as exc:
                exc_message = '%s\nValidation failed: %s. Skipping it...\n' % (''.join(exc.messages), data)
                self.handle_exception(exc_message)
            except Exception as exc:
                exc_message = '%s\nSomething unexpected occured: %s. Skipping it...\n' % (exc.message, data)
                self.handle_exception(exc_message)

        # Simple progress bar
        if (cnt % 10) == 0:                
            str_log = ImportActionHelper.get_progress_descriptor(
                'concepts', cnt, total, self.action_count)
            self.stdout.write(str_log, ending='\r')
            self.stdout.flush()
            if (cnt % 1000) == 0:
                logger.info(str_log)

    # Done with the input file, so close it
    self.concepts_file.close()

    # Import complete - display final progress bar
    str_log = ImportActionHelper.get_progress_descriptor(
        'concepts', cnt, total, self.action_count)
    self.stdout.write(str_log, ending='\r')
    self.stdout.flush()
    logger.info(str_log)

    # Log remaining unhandled IDs
    str_log = 'Remaining unhandled concept versions:\n'
    self.stdout.write(str_log, ending='\r')
    logger.info(str_log)
    str_log = ','.join(str(el) for el in self.concept_version_ids)
    self.stdout.write(str_log, ending='\r')
    self.stdout.flush()
    logger.info(str_log)

    # Deactivate old records
    if deactivate_old_records:
        str_log = 'Deactivating old concepts...\n'
        self.stdout.write(str_log)
        logger.info(str_log)
        for version_id in self.concept_version_ids:
            try:
                if self.remove_concept_version(version_id):
                    self.count_action(ImportActionHelper.IMPORT_ACTION_DEACTIVATE)

                    # Log the mapping deactivation
                    str_log = 'Deactivated concept version: %s\n' % version_id
                    self.stdout.write(str_log)
                    logger.info(str_log)

            except InvalidStateException as exc:
                str_log = 'Failed to inactivate concept version on ID %s! %s\n' % (version_id, exc.args[0])
                self.stderr.write(str_log)
                logger.warning(str_log)
    else:
        str_log = 'Skipping deactivation loop...\n'
        self.stdout.write(str_log)
        logger.info(str_log)

    # Display final summary
    str_log = 'Finished importing concepts!\n'
    self.stdout.write(str_log)
    logger.info(str_log)
    str_log = ImportActionHelper.get_progress_descriptor(
        'concepts', cnt, total, self.action_count)
    self.stdout.write(str_log, ending='\r')
    logger.info(str_log)

  def handle_exception(self, exception_message):
      self.stderr.write(exception_message)
      logger.warning(exception_message)
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
          try:
              self.concept_version_ids.remove(concept_version.id)
          except KeyError:
              str_log = 'Key not found. Could not remove key %s from list of concept version IDs: %s\n' % (concept_version.id, data)
              self.stderr.write(str_log)
              logger.warning(str_log)

          # Log the update
          if update_action:
              str_log = 'Updated concept, replacing version ID %s: %s\n' % (concept_version.id, data)
              self.stdout.write(str_log)
              logger.info(str_log)

      # Concept does not exist in OCL, so create new one
      except Concept.DoesNotExist:
          update_action = self.add_concept(source, data)

          # Log the insert
          if update_action:
              str_log = 'Created new concept: %s = %s\n' % (mnemonic, concept_name)
              self.stdout.write(str_log)
              logger.info(str_log)

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

  def create_concept_versions_map(self):
    #Create map for all concept ids to concept versions
    try:
      versions_list = ConceptVersion.objects.values('id','versioned_object_id').filter(id__in=self.concept_version_ids)
      self.concepts_versions_map = dict((x['versioned_object_id'], x['id']) for x in versions_list)
    except KeyError:
      str_log = "Map couldn't be created, possible corruption of data"
      raise InvalidStateException(str_log)
      