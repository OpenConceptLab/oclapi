from django.core.exceptions import ValidationError

from concepts.validation_messages import BASIC_DESCRIPTION_LOCALE, BASIC_NAME_LOCALE, BASIC_DESCRIPTION_TYPE, \
    BASIC_NAME_TYPE, BASIC_DATATYPE, BASIC_CONCEPT_CLASS, BASIC_DESCRIPTION_CANNOT_BE_EMPTY, \
    OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME, OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE
from oclapi.models import LOOKUP_CONCEPT_CLASSES

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
        self.lookup_attributes_should_be_valid()
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

    def lookup_attributes_should_be_valid(self):
        if self.concept.concept_class in LOOKUP_CONCEPT_CLASSES:
            return

        from orgs.models import Organization
        ocl_org_filter = Organization.objects.filter(mnemonic='OCL')

        if ocl_org_filter.count() < 1:
            raise ValidationError({'names': ['Lookup attributes must be imported']})

        org = ocl_org_filter.get()

        self.concept_class_should_be_valid_attribute(org)
        self.data_type_should_be_valid_attribute(org)
        self.name_type_should_be_valid_attribute(org)
        self.description_type_should_be_valid_attribute(org)
        self.locale_should_be_valid_attribute(org)

    def concept_class_should_be_valid_attribute(self, org):
        is_concept_class_valid = self.is_attribute_valid(self.concept.concept_class, org, 'Classes', 'Concept Class')

        if not is_concept_class_valid:
            raise ValidationError({'names': [BASIC_CONCEPT_CLASS]})

    def data_type_should_be_valid_attribute(self, org):
        is_data_type_valid = self.is_attribute_valid(self.concept.datatype, org, 'Datatypes', 'Datatype')

        if not is_data_type_valid:
            raise ValidationError({'names': [BASIC_DATATYPE]})

    def name_type_should_be_valid_attribute(self, org):
        if not self.concept.names:
            return

        for name in self.concept.names:
            if name.type in ['FULLY_SPECIFIED', 'SHORT']:
                continue

            if self.is_attribute_valid(name.type, org, 'NameTypes', 'NameType'):
                continue

            raise ValidationError({'names': [message_with_name_details(BASIC_NAME_TYPE, name)]})

    def description_type_should_be_valid_attribute(self, org):
        if not self.concept.descriptions:
            return

        description_type_count = len(
            filter(lambda d: self.is_attribute_valid(d.type, org, 'DescriptionTypes', 'DescriptionType'),
                   self.concept.descriptions))

        if description_type_count < len(self.concept.descriptions):
            raise ValidationError({'names': [BASIC_DESCRIPTION_TYPE]})

    def locale_should_be_valid_attribute(self, org):
        if not self.concept.names:
            return

        name_locale_count = len(
            filter(lambda n: self.is_attribute_valid(n.locale, org, 'Locales', 'Locale'),
                   self.concept.names))

        if name_locale_count < len(self.concept.names):
            raise ValidationError({'names': [BASIC_NAME_LOCALE]})

        if not self.concept.descriptions:
            return

        description_locale_count = len(
            filter(lambda d: self.is_attribute_valid(d.locale, org, 'Locales', 'Locale'),
                   self.concept.descriptions))

        if description_locale_count < len(self.concept.descriptions):
            raise ValidationError({'names': [BASIC_DESCRIPTION_LOCALE]})

    def is_attribute_valid(self, attribute_property, org, source_mnemonic, concept_class):
        from sources.models import Source
        from concepts.models import Concept

        attributetypes_source_filter = Source.objects.filter(parent_id=org.id, mnemonic=source_mnemonic)

        if attributetypes_source_filter.count() < 1:
            raise ValidationError({'names': ['Lookup attributes must be imported']})

        source_attributetypes = attributetypes_source_filter.values_list('id').get()

        matching_attribute_types = {'retired': False, 'is_active': True, 'concept_class': concept_class,
                                    'parent_id': source_attributetypes[0], 'names.name': attribute_property or 'None'}

        return Concept.objects.raw_query(matching_attribute_types).count() > 0
