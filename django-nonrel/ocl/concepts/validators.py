from django.core.exceptions import ValidationError

from concepts.validation_messages import  BASIC_DESCRIPTION_CANNOT_BE_EMPTY
def message_with_name_details(message, name):
    if name is None:
        return message

    name_str = name.name or 'n/a'
    locale = name.locale or 'n/a'
    preferred = 'yes' if name.locale_preferred else 'no'
    return unicode(u'{}: {} (locale: {}, preferred: {})'.format(message, unicode(name_str), locale, preferred))


class BasicConceptValidator:
    def __init__(self, concept):
        self.concept = concept

    def validate_concept_based(self):
        self.description_cannot_be_null()

    def validate_source_based(self):
        pass

    def description_cannot_be_null(self):
        if not self.concept.descriptions:
            return

        if len(self.concept.descriptions) == 0:
            return

        empty_descriptions = filter((lambda description: (not description.name) or (description.name == "")), self.concept.descriptions)

        if len(empty_descriptions):
            raise ValidationError({'descriptions': [BASIC_DESCRIPTION_CANNOT_BE_EMPTY]})
