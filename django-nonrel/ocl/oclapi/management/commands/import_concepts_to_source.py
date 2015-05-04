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
    help = 'Import concepts from a JSON file into a source'

    def do_import(self, user, source, input_file, options):

        logger.info('Import concepts to source...')
        self.source_version = SourceVersion.get_latest_version_of(source)
        if options['new_version']:
            try:
                new_version = SourceVersion.for_base_object(source, options['new_version'], previous_version=self.source_version)
                new_version.seed_concepts()
                new_version.seed_mappings()
                new_version.full_clean()
                new_version.save()
                self.source_version = new_version
            except Exception as e:
                raise CommandError('Failed to create new source version due to %s' % e.message)

        total = options.get('total', '(Unknown)')
        self.user = User.objects.filter(is_superuser=True)[0]
        self.concept_version_ids = set(self.source_version.concepts)
        cnt = 0
        for line in input_file:
            data = json.loads(line)
            cnt += 1
            # simple progress bar
            if (cnt % 10) == 0:
                self.stdout.write('%d of %d' % (cnt, total), ending='\r')
                self.stdout.flush()
            try:
                self.handle_concept(source, data)
            except IllegalInputException as e:
                self.stderr.write('\n%s' % e.message)
                self.stderr.write('\nFailed to parse line %s.  Skipping it...\n' % data)
                logger.warning('%s, failed to parse line %s, skipping it...' % (e.message, data))
            except InvalidStateException as e:
                self.stderr.write('\nSource is in an invalid state!')
                self.stderr.write('\n%s\n' % e.message)
                logger.warning('Source is in an invalid state: %s' % e.message)

        self.stdout.write('\nDeactivating old concepts...\n')
        logger.info('Deactivating old concepts...')

        for version_id in self.concept_version_ids:
            try:
                self.remove_concept_version(version_id)
            except InvalidStateException as e:
                self.stderr.write('Failed to inactivate concept! %s' % e.message)

        self.stdout.write('\nFinished importing concepts!\n')
        logger.info('Finished importing concepts!')

    def handle_concept(self, source, data):
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')
        try:
            concept = Concept.objects.get(parent_id=source.id, mnemonic=mnemonic)
        except Concept.DoesNotExist:
            self.add_concept(source, data)
            return
        try:
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id, id__in=self.source_version.concepts)
        except ConceptVersion.DoesNotExist:
            raise InvalidStateException("Source %s has concept %s, but source version %s does not." %
                                        (source.mnemonic, concept.mnemonic, self.source_version.mnemonic))

        self.update_concept_version(concept_version, data)
        self.concept_version_ids.remove(concept_version.id)
        return

    def add_concept(self, source, data):
        mnemonic = data['id']
        serializer = ConceptDetailSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new concept %s' % mnemonic)
        serializer.save(force_insert=True, parent_resource=source, child_list_attribute='concepts')
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new concept %s' % mnemonic)

    def update_concept_version(self, concept_version, data):
        diffs = {}
        clone = concept_version.clone()
        if 'retired' in data and clone.retired != data['retired']:
            diffs['retired'] = {'was': clone.retired, 'is': data['retired']}
        serializer = ConceptVersionUpdateSerializer(clone, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse concept to update: %s.' % concept_version.mnemonic)
        if serializer.is_valid():
            new_version = serializer.object
            if 'retired' in diffs:
                new_version.retired = data['retired']
            diffs.update(ConceptVersion.diff(concept_version, new_version))
            if diffs:
                if 'names' in diffs:
                    diffs['names'] = {'is': data.get('names')}
                if 'descriptions' in diffs:
                    diffs['descriptions'] = {'is': data.get('descriptions')}
                clone.update_comment = json.dumps(diffs)
                serializer.save()
                if not serializer.is_valid():
                    raise IllegalInputException('Could not persist update to concept: %s' % concept_version.mnemonic)

    def remove_concept_version(self, version_id):
        try:
            version = ConceptVersion.objects.get(id=version_id)
            version.is_active = False
            version.save()
        except:
            raise InvalidStateException("Cannot delete concept version %s because it doesn't exist!" % version_id)
