import json
import logging
from django.core.management import CommandError
from django.db.models import Q
from mappings.models import Mapping
from mappings.serializers import MappingCreateSerializer, MappingUpdateSerializer
from oclapi.management.commands import MockRequest
from sources.models import SourceVersion

__author__ = 'misternando'
logger = logging.getLogger('batch')


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
        self.count = 0
        self.add_count = 0
        self.update_count = 0
        self.remove_count = 0

    def log_counters(self):
        logger.info('progress %06d read, %06d added, %06d updated, %06d removed' %
            (self.count, self.add_count, self.update_count, self.remove_count))

    def import_mappings(self, new_version=False, total=0, **kwargs):
        logger.info('Import mappings to source...')
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
        self.count = 0
        for line in self.mappings_file:
            data = json.loads(line)
            self.count += 1
            # simple progress bar
            if (self.count % 10) == 0:
                self.stdout.write('%d of %d' % (self.count, total), ending='\r')
                self.stdout.flush()
            try:
                self.handle_mapping(data)
            except IllegalInputException as e:
                self.stderr.write('\n%s' % e)
                self.stderr.write('\nFailed to parse line %s.  Skipping it...\n' % data)
                logger.warning('%s, failed to parse line %s.  Skipping it...' % (e.message, data))
            except InvalidStateException as e:
                self.stderr.write('\nSource is in an invalid state!')
                self.stderr.write('\n%s\n' % e)
                logger.warning('%s, Source is in an invalid state!' % e.message)
            if (self.count % 1000) == 0:
                self.log_counters()

        self.log_counters()
        self.stdout.write('\nDeactivating old mappings...\n')
        logger.info('Deactivating old mappings...')

        deactivated = 0
        for mapping_id in self.mapping_ids:
            try:
                removed = self.remove_mapping(mapping_id)
                if removed:
                    deactivated += 1
            except InvalidStateException as e:
                self.stderr.write('Failed to inactivate mapping! %s' % e)
        self.stdout.write('\nDeactivated %s old mappings\n' % deactivated)

        self.log_counters()
        self.stdout.write('\nFinished importing mappings!\n')
        logger.info('Finished importing mappings!')

    def handle_mapping(self, data):
        serializer = MappingCreateSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not parse mapping %s due to %s' % (data,serializer.errors))
        try:
            mapping = serializer.save(commit=False)
            query = Q(parent_id=self.source.id, map_type=mapping.map_type, from_concept=mapping.from_concept)
            if mapping.to_concept:
                query = query & Q(to_concept=mapping.to_concept)
            else:
                query = query & Q(to_source_id=mapping.to_source.id, to_concept_code=mapping.to_concept_code, to_concept_name=mapping.to_concept_name)
            mapping = Mapping.objects.get(query)
        except Mapping.DoesNotExist:
            self.add_mapping(data)
            return
        if mapping.id not in self.source_version.mappings:
            raise InvalidStateException("Source %s has mapping %s, but source version %s does not." %
                                        (self.source.mnemonic, mapping.id, self.source_version.mnemonic))

        self.update_mapping(mapping, data)
        self.mapping_ids.remove(mapping.id)
        return

    def add_mapping(self, data):
        serializer = MappingCreateSerializer(data=data, context={'request': MockRequest(self.user)})
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new mapping due to %s' % serializer.errors)
        serializer.save(force_insert=True, parent_resource=self.source)
        if not serializer.is_valid():
            raise IllegalInputException('Could not persist new mapping due to %s' % serializer.errors)
        self.add_count += 1

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
                self.update_count += 1
                if not serializer.is_valid():
                    raise IllegalInputException('Could not persist update to mapping %s due to %s' % (mapping.id, serializer.errors))

    def remove_mapping(self, mapping_id):
        try:
            mapping = Mapping.objects.get(id=mapping_id)
            if mapping.is_active:
                mapping.is_active = False
                mapping.save()
                self.remove_count += 1
                return True
            return False
        except:
            raise InvalidStateException("Cannot delete mapping %s because it doesn't exist!" % mapping_id)


