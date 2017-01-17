from django.core.exceptions import ValidationError

from concepts.models import Concept
from mappings.custom_validators import OpenMRSMappingValidator
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from sources.models import Source

import os


class MappingValidationMixin:
    def clean(self):
        basic_errors = []

        try:
            if self.from_concept == self.to_concept:
                basic_errors.append("Cannot map concept to itself.")
        except Concept.DoesNotExist:
            basic_errors.append("Must specify a 'from_concept'.")

        if not (self.to_concept or (self.to_source and self.to_concept_code)):
            basic_errors.append("Must specify either 'to_concept' or 'to_source' & 'to_concept_code")

        if self.to_concept and (self.to_source or self.to_concept_code):
            basic_errors.append(
                "Must specify either 'to_concept' or 'to_source' & 'to_concept_code'. Cannot specify both.")

        if basic_errors:
            raise ValidationError(' '.join(basic_errors))

        if os.environ.get('DISABLE_VALIDATION'):
            return

        try:
            if self.parent_source.custom_validation_schema == CUSTOM_VALIDATION_SCHEMA_OPENMRS:
                custom_validator = OpenMRSMappingValidator(self)
                custom_validator.validate()
        except Source.DoesNotExist as err:
            raise ValidationError("There's no Source")

