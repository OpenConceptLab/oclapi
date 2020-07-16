import logging

from bson import ObjectId
from django.contrib.contenttypes.models import ContentType

from oclapi.rawqueries import RawQueries

logger = logging.getLogger('oclapi')

class ReferenceDefinition:
    _reference_definitions = None

    def __init__(self, source_type, source_field, target_type, use_object_id = True, nullable = False, list = False):
        self.source_type = source_type
        self.source_field = source_field
        self.target_type = target_type
        self.target_field = 'id'
        self.use_object_id = use_object_id
        self.nullable = nullable
        self._dependencies = None
        self.list = list

    @property
    def dependencies(self):
        if not self._dependencies:
            self._dependencies = self.__resolve_dependencies()
        return self._dependencies

    def __resolve_dependencies(self):
        dependencies = list()
        for reference_definition in ReferenceDefinition.get_reference_definitions():
            if reference_definition.target_type == self.source_type:
                dependencies.append(reference_definition)
        return dependencies

    @staticmethod
    def get_reference_definitions():
        if not ReferenceDefinition._reference_definitions:
            ReferenceDefinition._reference_definitions = ReferenceDefinition.__resolve_reference_definitions()
        return ReferenceDefinition._reference_definitions

    @staticmethod
    def __resolve_reference_definitions():
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
        from collection.models import CollectionConcept
        from collection.models import CollectionMapping
        return [
            ReferenceDefinition(Source, 'parent_id', Organization),
            ReferenceDefinition(Source, 'parent_id', UserProfile),
            ReferenceDefinition(Collection, 'parent_id', Organization),
            ReferenceDefinition(Collection, 'parent_id', UserProfile),

            ReferenceDefinition(ConceptVersion, 'source_version_ids', SourceVersion, False, False, True),
            ReferenceDefinition(ConceptVersion, 'versioned_object_id', Concept, False),
            ReferenceDefinition(ConceptVersion, 'previous_version', ConceptVersion),
            ReferenceDefinition(ConceptVersion, 'parent_version', ConceptVersion),
            ReferenceDefinition(ConceptVersion, 'root_version', ConceptVersion),

            ReferenceDefinition(MappingVersion, 'source_version_ids', SourceVersion, False, False, True),
            ReferenceDefinition(MappingVersion, 'versioned_object_id', Mapping, False),
            ReferenceDefinition(MappingVersion, 'previous_version', MappingVersion),
            ReferenceDefinition(MappingVersion, 'parent_version', MappingVersion),

            ReferenceDefinition(Mapping, 'to_concept', Concept, True, True),
            ReferenceDefinition(Mapping, 'from_concept', Concept, True, True),
            ReferenceDefinition(MappingVersion, 'to_concept', Concept, True, True),
            ReferenceDefinition(MappingVersion, 'from_concept', Concept, True, True),

            ReferenceDefinition(SourceVersion, 'versioned_object_id', Source, False),
            ReferenceDefinition(SourceVersion, 'previous_version', SourceVersion),
            ReferenceDefinition(SourceVersion, 'parent_version', SourceVersion),

            ReferenceDefinition(CollectionVersion, 'versioned_object_id', Collection, False),
            ReferenceDefinition(CollectionVersion, 'previous_version', CollectionVersion),
            ReferenceDefinition(CollectionVersion, 'parent_version', CollectionVersion),

            ReferenceDefinition(CollectionConcept, 'collection_id', CollectionVersion, False),
            ReferenceDefinition(CollectionConcept, 'concept_id', ConceptVersion, False),

            ReferenceDefinition(CollectionMapping, 'mapping_id', MappingVersion, False),
            ReferenceDefinition(CollectionMapping, 'collection_id', CollectionVersion, False),

            ReferenceDefinition(UserProfile, 'organizations', Organization, False, True, True),

            ReferenceDefinition(Organization, 'members', UserProfile, False, True, True)
        ]

class Reference:
    def __init__(self, reference_definition, source_id, target_id):
        self.reference_definition = reference_definition
        self.source_id = source_id
        self.target_id = target_id
        self.dependencies = Reference.__get_dependencies(reference_definition, source_id)
        self.deletable = (not self.dependencies)
        self.item = RawQueries().find_by_id(reference_definition.source_type, source_id)
        self.deleted = False

    @staticmethod
    def find_broken_references():
        ref_defs = ReferenceDefinition.get_reference_definitions()
        candidates = {}
        reference_list = ReferenceList()
        for ref_def in ref_defs:
            Reference.__find_broken_references_for_definition(ref_def, reference_list, candidates)

        if reference_list.broken_total_count() != 0:
            logger.error('Found %d broken references' % reference_list.broken_total_count())
        else:
            logger.info('No broken references found')

        return reference_list

    @staticmethod
    def __find_broken_references_for_definition(reference_definition, reference_list, candidates):
        ref_def_target = reference_definition.target_type.__name__ + '.' + reference_definition.target_field
        ref_def_target_key = ref_def_target + '.%d' % reference_definition.use_object_id
        ref_def_source = reference_definition.source_type.__name__ + '.' + reference_definition.source_field

        if ref_def_target_key not in candidates:
            reference_candidates = list(reference_definition.target_type.objects.values_list(reference_definition.target_field, flat=True))
            if reference_definition.use_object_id:
                ref_candidates_id = []
                for id in reference_candidates:
                    if isinstance(id, ObjectId):
                        ref_candidates_id.append(id)
                    else:
                        ref_candidates_id.append(ObjectId(id))
                reference_candidates = ref_candidates_id
            reference_candidates.append(None)
            candidates[ref_def_target_key] = reference_candidates
        else:
            reference_candidates = candidates[ref_def_target_key]

        logger.info('Checking references in %s against %d candidates from %s' %
                    (ref_def_source, len(reference_candidates), ref_def_target))
        reference_list.update_target_candidate_count(reference_definition, len(reference_candidates))

        source_field_in = reference_definition.source_field + '__in'
        target_ids_query = reference_definition.source_type.objects.exclude(**{source_field_in: reference_candidates})
        if ref_def_source == 'Source.parent_id' or ref_def_source == 'Collection.parent_id':
            content_type = ContentType.objects.get_for_model(reference_definition.target_type)
            target_ids_query = target_ids_query.filter(parent_type=content_type)

        broken_count = 0
        for (source_id, target_ids) in target_ids_query.values_list('id', reference_definition.source_field):
            if isinstance(target_ids, list) or isinstance(target_ids, set):
                target_ids = list(set(target_ids).difference(reference_candidates))
            else:
                target_ids = [target_ids]

            if not target_ids and not reference_definition.nullable:
                reference_list.add_broken_reference(Reference(reference_definition, source_id, None))
                broken_count += 1
            else:
                for target_id in target_ids:
                    reference_list.add_broken_reference(Reference(reference_definition, source_id, target_id))
                    broken_count += 1

        logger.info('Found %d broken references in %s' %
                    (broken_count, ref_def_source))

    @staticmethod
    def __get_dependencies(reference_definition, source_id):
        dependencies = []
        for dependency in reference_definition.dependencies:
            raw_source_id = source_id
            raw_source_field = dependency.source_field
            if dependency.use_object_id:
                raw_source_id = ObjectId(source_id)
                raw_source_field = dependency.source_field + '_id'

            items = RawQueries().find_by_field(dependency.source_type, raw_source_field, raw_source_id)
            for item in items:
                if dependency.source_type is reference_definition.source_type and item['_id'] == raw_source_id:
                    continue #exclude self referencing dependencies
                dependencies.append('%s.%s: %s' % (dependency.source_type.__name__, dependency.source_field, str(item)))
        return dependencies


class ReferenceList:
    def __init__(self):
        self.items = []

    def get_item(self, reference_definition):
        for item in self.items:
            if item.reference_definition.source_type is reference_definition.source_type and item.reference_definition.source_field is reference_definition.source_field:
                return item

        item = ReferenceListItem(reference_definition)
        self.items.append(item)
        return item

    def update_target_candidate_count(self, reference_definition, candidate_count):
        item = self.get_item(reference_definition)
        item.target_candidate_count += candidate_count

    def add_broken_reference(self, broken_reference):
        item = self.get_item(broken_reference.reference_definition)
        item.broken_references.append(broken_reference)
        item.broken_count += 1
        if broken_reference.deletable:
            item.deletable_count += 1

    def broken_total_count(self):
        result = 0
        for item in self.items:
            result += item.broken_count
        return result

    def deletable_total_count(self):
        result = 0
        for item in self.items:
            result += item.deletable_count
        return result

    def delete(self, force = False):
        broken_references_by_type = {}

        for item in self.items:
            for broken_reference in item.broken_references:
                if broken_reference.deletable or force:
                    source_type = broken_reference.reference_definition.source_type
                    if source_type in broken_references_by_type:
                        broken_references_by_type[source_type].append(broken_reference)
                    else:
                        broken_references_by_type[source_type] = [broken_reference]

        for source_type in broken_references_by_type:
            ids = []
            broken_references = broken_references_by_type[source_type]
            for broken_reference in broken_references:
                if broken_reference.reference_definition.list:
                    RawQueries().bulk_delete_from_list(source_type, [broken_reference.source_id],
                                                       broken_reference.reference_definition.source_field,
                                                       [broken_reference.target_id])
                else:
                    ids.append(broken_reference.source_id)
            if ids:
                RawQueries().bulk_delete(source_type, ids)

            for broken_reference in broken_references_by_type[source_type]:
                broken_reference.deleted = True

class ReferenceListItem:
    def __init__(self, reference_definition):
        self.reference_definition = reference_definition
        self.source = '%s.%s' % (reference_definition.source_type.__name__, reference_definition.source_field)
        self.target = '%s.%s' % (reference_definition.target_type.__name__, reference_definition.target_field)
        self.target_candidate_count = 0
        self.broken_count = 0
        self.deletable_count = 0
        self.broken_references = []