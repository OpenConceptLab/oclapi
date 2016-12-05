from django.core.exceptions import ValidationError

from mappings.validation_messages import OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS

class OpenMRSMappingValidator:
    def __init__(self, mapping):
        self.mapping = mapping

    def validate(self):
        self.pair_must_be_unique()

    def pair_must_be_unique(self):
        from mappings.models import Mapping

        intersection = Mapping.objects.filter(parent=self.mapping.parent_source, from_concept=self.mapping.from_concept,
                                              to_concept=self.mapping.to_concept, is_active=True, retired=False).count()

        if intersection:
            raise ValidationError(OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS)
