import logging

from bson import ObjectId
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger('oclapi')

class ReferenceDefinition:
    def __init__(self, source_type, source_field, target_type, target_field='id', use_object_id = True):
        self.source_type = source_type
        self.source_field = source_field
        self.target_type = target_type
        self.target_field = target_field
        self.use_object_id = use_object_id

    @staticmethod
    def get_reference_definitions():
        from mappings.models import MappingVersion
        from sources.models import SourceVersion
        from concepts.models import ConceptVersion
        from concepts.models import Concept
        from mappings.models import Mapping
        from sources.models import Source
        from collection.models import CollectionVersion
        from collection.models import Collection
        from users.models import UserProfile
        from orgs.models import Organization
        return [
            ReferenceDefinition(Source, 'parent_id', Organization),
            ReferenceDefinition(Source, 'parent_id', UserProfile),
            ReferenceDefinition(Collection, 'parent_id', Organization),
            ReferenceDefinition(Collection, 'parent_id', UserProfile),

            ReferenceDefinition(ConceptVersion, 'source_version_ids', SourceVersion, 'id', False),
            ReferenceDefinition(ConceptVersion, 'versioned_object_id', Concept),
            ReferenceDefinition(ConceptVersion, 'previous_version', ConceptVersion),
            ReferenceDefinition(ConceptVersion, 'parent_version', ConceptVersion),
            ReferenceDefinition(ConceptVersion, 'root_version', ConceptVersion),

            ReferenceDefinition(MappingVersion, 'source_version_ids', SourceVersion, 'id', False),
            ReferenceDefinition(MappingVersion, 'versioned_object_id', Mapping),
            ReferenceDefinition(MappingVersion, 'previous_version', MappingVersion),
            ReferenceDefinition(MappingVersion, 'parent_version', MappingVersion),

            ReferenceDefinition(SourceVersion, 'versioned_object_id', Source),
            ReferenceDefinition(SourceVersion, 'previous_version', SourceVersion),
            ReferenceDefinition(SourceVersion, 'parent_version', SourceVersion),

            ReferenceDefinition(CollectionVersion, 'versioned_object_id', Collection),
            ReferenceDefinition(CollectionVersion, 'previous_version', CollectionVersion),
            ReferenceDefinition(CollectionVersion, 'parent_version', CollectionVersion),

            ReferenceDefinition(UserProfile, 'organizations', Organization, 'id', False),

            ReferenceDefinition(Organization, 'members', UserProfile, 'id', False)
        ]

class Reference:
    def __init__(self, reference_definition, source_id, broken_reference):
        self.reference_definition = reference_definition
        self.source_id = source_id
        self.broken_reference = broken_reference

    @staticmethod
    def find_broken_references():
        ref_defs = ReferenceDefinition.get_reference_definitions()
        candidates = {}
        broken_references = ReferenceList()
        for ref_def in ref_defs:
            Reference.__find_broken_references_for_definition(ref_def, broken_references, candidates)

        if broken_references.broken_total_count() != 0:
            logger.error('Found %d broken references' % broken_references.broken_total_count())
        else:
            logger.info('No broken references found')

        return broken_references

    @staticmethod
    def __find_broken_references_for_definition(reference_definition, broken_references, candidates):
        ref_def_target = reference_definition.target_type.__name__ + '.' + reference_definition.target_field
        ref_def_target_key = ref_def_target + '.%d' % reference_definition.use_object_id
        ref_def_source = reference_definition.source_type.__name__ + '.' + reference_definition.source_field

        broken_references.add_broken_count(ref_def_source)

        if ref_def_target_key not in candidates:
            reference_candidates = list(reference_definition.target_type.objects.values_list(reference_definition.target_field, flat=True))
            if reference_definition.use_object_id:
                reference_candidates = [ObjectId(id) for id in reference_candidates]
            reference_candidates.append(None)
            candidates[ref_def_target_key] = reference_candidates
        else:
            reference_candidates = candidates[ref_def_target_key]

        logger.info('Checking references in %s against %d candidates from %s' %
                    (ref_def_source, len(reference_candidates), ref_def_target))
        broken_references.add_candidate_count(reference_definition.target_type.__name__, len(reference_candidates))

        source_field_in = reference_definition.source_field + '__in'
        broken_references_query = reference_definition.source_type.objects.exclude(**{source_field_in: reference_candidates})
        if ref_def_source == 'Source.parent_id' or ref_def_source == 'Collection.parent_id':
            content_type = ContentType.objects.get_for_model(reference_definition.target_type)
            broken_references_query = broken_references_query.filter(parent_type=content_type)

        for (source_id, broken_reference_list) in broken_references_query.values_list('id', reference_definition.source_field):
            if isinstance(broken_reference_list, list) or isinstance(broken_reference_list, set):
                broken_reference_list = list(set(broken_reference_list).difference(reference_candidates))
            else:
                broken_reference_list = [broken_reference_list]

            if not broken_reference_list:
                broken_references.append(Reference(reference_definition, source_id, None))

            for broken_reference in broken_reference_list:
                broken_references.append(Reference(reference_definition, source_id, broken_reference))


class ReferenceList:
    def __init__(self):
        self.broken_references = []
        self.broken_counts = {}
        self.candidate_counts = {}

    def append(self, broken_reference):
        self.broken_references.append(broken_reference)
        broken_reference_key = broken_reference.reference_definition.source_type.__name__ + '.' + broken_reference.reference_definition.source_field
        if broken_reference_key in self.broken_counts:
            self.broken_counts[broken_reference_key] += 1

    def add_broken_count(self, broken_reference_key):
        if broken_reference_key not in self.broken_counts:
            self.broken_counts[broken_reference_key] = 0

    def add_candidate_count(self, target_type, target_count):
        self.candidate_counts[target_type] = target_count

    def broken_total_count(self):
        return len(self.broken_references)