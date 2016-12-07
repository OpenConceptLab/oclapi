from django.core.exceptions import ValidationError

from concepts.validation_messages import BASIC_DESCRIPTION_LOCALE, BASIC_NAME_LOCALE, BASIC_DESCRIPTION_TYPE, \
    BASIC_NAME_TYPE, BASIC_DATATYPE, BASIC_CONCEPT_CLASS, BASIC_DESCRIPTION_CANNOT_BE_EMPTY, \
    BASIC_AT_LEAST_ONE_FULLY_SPECIFIED_NAME, BASIC_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE
from oclapi.models import LOOKUP_CONCEPT_CLASSES

def message_with_name_details(message, name):
    if name is None:
        return message

    name_str = name.name or 'n/a'
    locale = name.locale or 'n/a'
    preferred = 'yes' if name.locale_preferred else 'no'
    return str.format('{}: {} (locale: {}, preferred: {})', message, name_str, locale, preferred)


class BasicConceptValidator:
    def __init__(self, concept):
        self.concept = concept

    def validate_concept_based(self):
        self.lookup_attributes_should_be_valid()
        self.description_cannot_be_null()
        self.requires_at_least_one_fully_specified_name()

    def validate_source_based(self):
        self.preferred_name_should_be_unique_for_source_and_locale()

    def preferred_name_should_be_unique_for_source_and_locale(self):
        from concepts.models import Concept, ConceptVersion

        # Concept preferred_name should be unique for same source and locale.
        preferred_names_in_concept = dict()
        self_id = getattr(self.concept, "versioned_object_id", None)

        for name in [n for n in self.concept.names if n.locale_preferred]:
            validation_error = {'names': [message_with_name_details(BASIC_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE, name)]}

            # making sure names in the submitted concept meet the same rule
            name_key = name.locale + name.name
            if name_key in preferred_names_in_concept:
                raise ValidationError(validation_error)

            preferred_names_in_concept[name_key] = True

            other_concepts_in_source = list(Concept.objects \
                                            .filter(parent_id=self.concept.parent_source.id, is_active=True,
                                                    retired=False) \
                                            .exclude(id=self_id) \
                                            .values_list('id', flat=True))

            if len(other_concepts_in_source) < 1:
                continue

            same_name_and_locale = {'versioned_object_id': {'$in': other_concepts_in_source},
                                    'names': {'$elemMatch': {'name': name.name, 'locale': name.locale, 'type': {'$nin': ['Short', 'SHORT']}}},
                                    'is_latest_version': True}

            if ConceptVersion.objects.raw_query(same_name_and_locale).count() > 0:
                raise ValidationError(validation_error)

    def requires_at_least_one_fully_specified_name(self):
        # A concept must have at least one fully specified name (across all locales)
        fully_specified_name_count = len(
            filter(lambda n: n.is_fully_specified, self.concept.names))
        if fully_specified_name_count < 1:
            raise ValidationError({'names': [BASIC_AT_LEAST_ONE_FULLY_SPECIFIED_NAME]})

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

        name_type_count = len(
            filter(lambda n: self.is_attribute_valid(n.type, org, 'NameTypes', 'NameType'), self.concept.names))

        if name_type_count < len(self.concept.names):
            raise ValidationError({'names': [BASIC_NAME_TYPE]})

    def description_type_should_be_valid_attribute(self, org):
        if not self.concept.descriptions:
            return

        description_type_count = len(
            filter(lambda d: self.is_attribute_valid(d.type, org, 'DescriptionTypes', 'DescriptionType'),
                   self.concept.descriptions))

        if description_type_count < len(self.concept.descriptions):
            raise ValidationError({'names': [BASIC_DESCRIPTION_TYPE]})

    def locale_should_be_valid_attribute(self, org):
        if not self.concept.names or not self.concept.descriptions:
            return

        name_locale_count = len(
            filter(lambda n: self.is_attribute_valid(n.locale, org, 'Locales', 'Locale'),
                   self.concept.names))

        if name_locale_count < len(self.concept.names):
            raise ValidationError({'names': [BASIC_NAME_LOCALE]})

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
                                    'parent_id': source_attributetypes[0], 'names.name': attribute_property}

        return Concept.objects.raw_query(matching_attribute_types).count() > 0
