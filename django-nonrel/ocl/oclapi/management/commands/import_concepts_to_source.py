import json
from optparse import make_option
import os.path
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from concepts.models import Concept, ConceptVersion
from concepts.serializers import ConceptDetailSerializer, ConceptVersionUpdateSerializer
from sources.models import Source, SourceVersion

__author__ = 'misternando'


class IllegalInputException(BaseException): pass


class InvalidStateException(BaseException): pass


class Command(BaseCommand):
    args = '[source_id] [concepts input file]'
    help = 'Import concepts from a JSON file into a source'
    option_list = BaseCommand.option_list + (
        make_option('--create-source-version',
                    action='store',
                    dest='new_version',
                    default=None,
                    help='Import concepts to new version of source.'),
    )

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Wrong number of arguments.  (Got %s; expected 2)' % len(args))

        source_id = args[0]
        try:
            self.source = Source.objects.get(id=source_id)
        except Source.DoesNotExist:
            raise CommandError('Could not find source with id=%s' % source_id)

        input_file = args[1]
        if not os.path.exists(input_file):
            raise CommandError('Could not find input file %s' % input_file)

        try:
            self.input = open(input_file, 'rb')
        except IOError:
            raise CommandError('Could not open input file %s' % input_file)

        self.source_version = SourceVersion.get_latest_version_of(self.source)
        if options['new_version']:
            try:
                new_version = SourceVersion.for_base_object(self.source, options['new_version'], previous_version=self.source_version)
                new_version.seed_concepts()
                new_version.full_clean()
                new_version.save()
                self.source_version = new_version
            except Exception as e:
                raise CommandError('Failed to create new source version due to %s' % e.message)

        self.user = User.objects.filter(is_superuser=True)[0]
        self.concept_version_ids = set(self.source_version.concepts)
        self.stdout.write('Adding/updating new concepts...\n')
        for line in self.input:
            data = json.loads(line)
            try:
                self.handle_concept(data)
                self.stdout.write('.')
            except IllegalInputException as e:
                self.stderr.write('\n%s' % e.message)
                self.stderr.write('\nFailed to parse line %s.  Skipping it...\n' % data)
            except InvalidStateException as e:
                self.stderr.write('\nSource is in an invalid state!')
                self.stderr.write('\n%s\n' % e.message)

        self.stdout.write('\nDeactivating old concepts...\n')
        for version_id in self.concept_version_ids:
            try:
                self.remove_concept_version(version_id)
            except InvalidStateException as e:
                self.stderr.write('Failed to inactivate concept! %s' % e.message)
            self.stdout.write('.')

        self.stdout.write('\nFinished importing concepts!\n')

    def handle_concept(self, data):
        mnemonic = data['id']
        if not mnemonic:
            raise IllegalInputException('Must specify concept id.')
        try:
            concept = Concept.objects.get(parent_id=self.source.id, mnemonic=mnemonic)
        except Concept.DoesNotExist:
            self.add_concept(data)
            return
        try:
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id, id__in=self.source_version.concepts)
        except ConceptVersion.DoesNotExist:
            raise InvalidStateException("Source %s has concept %s, but source version %s does not." %
                                        (self.source.mnemonic, concept.mnemonic, self.source_version.mnemonic))

        self.update_concept_version(concept_version, data)
        self.concept_version_ids.remove(concept_version.id)
        return

    def add_concept(self, data):
        mnemonic = data['id']
        serializer = ConceptDetailSerializer(data=data)
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new concept %s' % mnemonic)
        serializer.save(force_insert=True, owner=self.user, parent_resource=self.source, child_list_attribute='concepts')
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new concept %s' % mnemonic)

    def update_concept_version(self, concept_version, data):
        diffs = {}
        clone = concept_version.clone()
        if 'retired' in data and clone.retired != data['retired']:
            diffs['retired'] = {'was': clone.retired, 'is': data['retired']}
        serializer = ConceptVersionUpdateSerializer(clone, data=data)
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
                serializer.save(user=self.user)
                if not serializer.is_valid():
                    raise IllegalInputException('Could not persist update to concept: %s' % concept_version.mnemonic)

    def remove_concept_version(self, version_id):
        try:
            version = ConceptVersion.objects.get(id=version_id)
            version.is_active = False
            version.save()
        except:
            raise InvalidStateException("Cannot delete concept version %s because it doesn't exist!" % version_id)
