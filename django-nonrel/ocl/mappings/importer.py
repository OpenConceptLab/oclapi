import json
from django.core.management import CommandError
from mappings.models import Mapping
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer
from oclapi.importer import MockRequest
from sources.models import SourceVersion

__author__ = 'misternando'


class IllegalInputException(BaseException):
    pass


class InvalidStateException(BaseException):
    pass


class MappingsImporter(object):

    def __init__(self, source, mappings_file, output_stream, error_stream, user):
        self.source = source
        self.mappings_file = mappings_file
        self.stdout = output_stream
        self.stderr = error_stream
        self.user = user

    def import_mappings(self, new_version=False):
        self.source_version = SourceVersion.get_latest_version_of(self.source)
        if new_version:
            try:
                new_version = SourceVersion.for_base_object(self.source, new_version, previous_version=self.source_version)
                new_version.seed_concepts()
                new_version.seed_mappings()
                new_version.full_clean()
                new_version.save()
                self.source_version = new_version
            except Exception as e:
                raise CommandError('Failed to create new source version due to %s' % e.message)

        self.mapping_ids = set(self.source_version.mappings)
        cnt = 0
        for line in self.mappings_file:
            data = json.loads(line)
            cnt += 1
            # simple progress bar
            if (cnt % 10) == 0:
                self.stdout.write('%d of %d' % (cnt, self.limit), ending='\r')
                self.stdout.flush()
            try:
                self.handle_mapping(data)
            except IllegalInputException as e:
                self.stderr.write('\n%s' % e)
                self.stderr.write('\nFailed to parse line %s.  Skipping it...\n' % data)
            except InvalidStateException as e:
                self.stderr.write('\nSource is in an invalid state!')
                self.stderr.write('\n%s\n' % e)

        self.stdout.write('\nDeactivating old mappings...\n')
        for mapping_id in self.mapping_ids:
            try:
                self.remove_mapping(mapping_id)
            except InvalidStateException as e:
                self.stderr.write('Failed to inactivate mapping! %s' % e.message)
            self.stdout.write('.')

        self.stdout.write('\nFinished importing mappings!\n')

    def handle_mapping(self, data):
        external_id = data.get('external_id')
        if not external_id:
            raise IllegalInputException('Must specify mapping external_id.')
        try:
            mapping = Mapping.objects.get(parent_id=self.source.id, external_id=external_id)
        except Mapping.DoesNotExist:
            self.add_mapping(data)
            return
        if mapping.id not in self.source_version.mappings:
            raise InvalidStateException("Source %s has concept %s, but source version %s does not." %
                                        (self.source.mnemonic, mapping.id, self.source_version.mnemonic))

        self.update_mapping(mapping, data)
        self.mapping_ids.remove(mapping.id)
        return

    def add_mapping(self, data):
        external_id = data['external_id']
        serializer = MappingCreateSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse new mapping %s due to %s' % (data,serializer.errors))
        serializer.save(force_insert=True, parent_resource=self.source)
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new mapping %s due to %s' % (external_id, serializer.errors))

    def update_mapping(self, mapping, data):
        diffs = {}
        if 'retired' in data and mapping.retired != data['retired']:
            diffs['retired'] = {'was': mapping.retired, 'is': data['retired']}
        original = mapping.clone(self.user)
        serializer = MappingUpdateSerializer(mapping, data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse mapping to update mapping %s due to %s.' % (mapping.id, serializer.errors))
        if serializer.is_valid():
            mapping = serializer.object
            if 'retired' in diffs:
                mapping.retired = data['retired']
            diffs.update(Mapping.diff(original, mapping))
            if diffs:
                serializer.save()
                if not serializer.is_valid():
                    raise IllegalInputException('Could not persist update to mapping %s due to %s' % (mapping.id, serializer.errors))

    def remove_mapping(self, mapping_id):
        try:
            mapping = Mapping.objects.get(id=mapping_id)
            mapping.is_active = False
            mapping.save()
        except:
            raise InvalidStateException("Cannot delete concept version %s because it doesn't exist!" % mapping_id)


