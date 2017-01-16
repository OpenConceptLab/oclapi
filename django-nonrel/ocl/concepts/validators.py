from django.core.exceptions import ValidationError

from concepts.validation_messages import  BASIC_DESCRIPTION_CANNOT_BE_EMPTY, BASIC_NAMES_CANNOT_BE_EMPTY
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS


def message_with_name_details(message, name):
    if name is None:
        return message

    name_str = name.name or 'n/a'
    locale = name.locale or 'n/a'
    preferred = 'yes' if name.locale_preferred else 'no'
    return unicode(u'{}: {} (locale: {}, preferred: {})'.format(message, unicode(name_str), locale, preferred))

class ValidatorSelector:
    def __init__(self, validation_schema=None):
        from concepts.custom_validators import OpenMRSConceptValidator

        validator_map = {
            CUSTOM_VALIDATION_SCHEMA_OPENMRS: OpenMRSConceptValidator
        }

        self.validator_class = validator_map.get(validation_schema, BasicConceptValidator)

    def get_validator(self, concept):
        return self.validator_class(concept)



class BaseConceptValidator:
    def validate(self):
        self.validate_concept_based()
        self.validate_source_based()

    def validate_concept_based(self):
        pass

    def validate_source_based(self):
        pass

class BasicConceptValidator(BaseConceptValidator):
    def __init__(self, concept):
        self.concept = concept

    def validate_concept_based(self):
        self.description_cannot_be_null()
        self.must_have_at_least_one_name()

    def validate_source_based(self):
        pass

    def must_have_at_least_one_name(self):
        if self.concept.names and len(self.concept.names) > 0:
            return

        raise ValidationError({'names': [BASIC_NAMES_CANNOT_BE_EMPTY]})

    def description_cannot_be_null(self):
        if not self.concept.descriptions:
            return

        if len(self.concept.descriptions) == 0:
            return

        empty_descriptions = filter((lambda description: (not description.name) or (description.name == "")), self.concept.descriptions)

        if len(empty_descriptions):
            raise ValidationError({'descriptions': [BASIC_DESCRIPTION_CANNOT_BE_EMPTY]})
