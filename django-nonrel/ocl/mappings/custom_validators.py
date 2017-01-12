from django.core.exceptions import ValidationError

from mappings.validation_messages import OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS, OPENMRS_MAPTYPE
from oclapi.models import LOOKUP_CONCEPT_CLASSES

class OpenMRSMappingValidator:
    def __init__(self, mapping):
        self.mapping = mapping

    def validate(self):
        self.pair_must_be_unique()
        self.lookup_attributes_should_be_valid()

    def pair_must_be_unique(self):
        from mappings.models import Mapping

        intersection = Mapping.objects.filter(parent=self.mapping.parent_source, from_concept=self.mapping.from_concept,
                                              to_concept=self.mapping.to_concept, is_active=True, retired=False).count()

        if intersection:
            raise ValidationError(OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS)

    def map_type_should_be_valid_attribute(self, org):
        is_data_type_valid = self.is_attribute_valid(self.concept.datatype, org, 'MapTypes', 'MapType')

        if not is_data_type_valid:
            raise ValidationError({'map_type': [OPENMRS_MAPTYPE]})

    def is_attribute_valid(self, attribute_property, org, source_mnemonic, concept_class):
        from sources.models import Source
        from concepts.models import Concept

        attributetypes_source_filter = Source.objects.filter(parent_id=org.id, mnemonic=source_mnemonic)

        if attributetypes_source_filter.count() < 1:
            raise ValidationError({'non_field_errors': ['Lookup attributes must be imported']})

        source_attributetypes = attributetypes_source_filter.values_list('id').get()

        matching_attribute_types = {'retired': False, 'is_active': True, 'concept_class': concept_class,
                                    'parent_id': source_attributetypes[0], 'names.name': attribute_property or 'None'}

        return Concept.objects.raw_query(matching_attribute_types).count() > 0

    def lookup_attributes_should_be_valid(self):
        if self.concept.concept_class in LOOKUP_CONCEPT_CLASSES:
            return

        from orgs.models import Organization
        ocl_org_filter = Organization.objects.filter(mnemonic='OCL')

        if ocl_org_filter.count() < 1:
            raise ValidationError({'non_field_errors': ['Lookup attributes must be imported']})

        org = ocl_org_filter.get()

        self.map_type_should_be_valid_attribute(org)
