from django.core.exceptions import ValidationError

from concepts.validation_messages import OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE, \
    OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE, OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE, \
    OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, \
    OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED, OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME, \
    OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE, OPENMRS_CONCEPT_CLASS, OPENMRS_DATATYPE, OPENMRS_NAME_TYPE, \
    OPENMRS_DESCRIPTION_TYPE, OPENMRS_NAME_LOCALE, OPENMRS_DESCRIPTION_LOCALE
from concepts.validators import message_with_name_details, BaseConceptValidator
from oclapi.models import LOOKUP_CONCEPT_CLASSES


class OpenMRSConceptValidator(BaseConceptValidator):
    def __init__(self, concept):
        self.concept = concept

    def validate_concept_based(self):
        self.must_have_exactly_one_preferred_name()
        self.all_non_short_names_must_be_unique()
        self.no_more_than_one_short_name_per_locale()
        self.short_name_cannot_be_marked_as_locale_preferred()
        self.only_one_fully_specified_name_per_locale()
        self.requires_at_least_one_fully_specified_name()
        self.lookup_attributes_should_be_valid()

    def validate_source_based(self):
        self.must_have_unique_fully_specified_name_for_same_source_and_locale()
        self.preferred_name_should_be_unique_for_source_and_locale()

    def must_have_exactly_one_preferred_name(self):
        preferred_name_locales_in_concept = dict()

        for name in self.concept.names:
            if not name.locale_preferred:
                continue

            if name.locale in preferred_name_locales_in_concept:
                raise ValidationError({
                    'names': [message_with_name_details(OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, name)]
                })

            preferred_name_locales_in_concept[name.locale] = True

    def requires_at_least_one_fully_specified_name(self):
        # A concept must have at least one fully specified name (across all locales)
        fully_specified_name_count = len(
            filter(lambda n: n.is_fully_specified, self.concept.names))
        if fully_specified_name_count < 1:
            raise ValidationError({'names': [OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME]})

    def preferred_name_should_be_unique_for_source_and_locale(self):
        from concepts.models import Concept, ConceptVersion

        # Concept preferred_name should be unique for same source and locale.
        preferred_names_dict = dict()
        self_id = getattr(self.concept, 'versioned_object_id', getattr(self.concept, 'id', None))

        preferred_names_list = [n for n in self.concept.names if n.locale_preferred]
        for name in preferred_names_list:
            validation_error = {
                'names': [message_with_name_details(OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE, name)]}

            # making sure names in the submitted concept meet the same rule
            name_key = name.locale + name.name
            if name_key in preferred_names_dict:
                raise ValidationError(validation_error)

            preferred_names_dict[name_key] = True

            other_concepts_in_source = list(Concept.objects
                                            .filter(parent_id=self.concept.parent_source.id, is_active=True,
                                                    retired=False)
                                            .exclude(id=self_id)
                                            .values_list('id', flat=True))

            if len(other_concepts_in_source) < 1:
                continue

            same_name_and_locale = {'versioned_object_id': {'$in': other_concepts_in_source},
                                    'names': {'$elemMatch': {'name': name.name, 'locale': name.locale,
                                                             'type': {'$nin': ['Short', 'SHORT']}}},
                                    'is_latest_version': True}

            if ConceptVersion.objects.raw_query(same_name_and_locale).count() > 0:
                raise ValidationError(validation_error)

    def must_have_unique_fully_specified_name_for_same_source_and_locale(self):
        from concepts.models import Concept, ConceptVersion
        fully_specified_names_in_concept = dict()
        self_id = getattr(self.concept, 'versioned_object_id', getattr(self.concept, 'id', None))

        for name in [n for n in self.concept.names if n.is_fully_specified]:
            # Concept preferred_name should be unique for same source and locale.
            validation_error = {'names': [
                message_with_name_details(OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, name)]}
            # making sure names in the submitted concept meet the same rule
            name_key = name.locale + name.name
            if name_key in fully_specified_names_in_concept:
                raise ValidationError(validation_error)

            fully_specified_names_in_concept[name_key] = True

            other_concepts_in_source = list(Concept.objects \
                                            .filter(parent_id=self.concept.parent_source.id, is_active=True,
                                                    retired=False) \
                                            .exclude(id=self_id) \
                                            .values_list('id', flat=True))

            if len(other_concepts_in_source) < 1:
                continue

            same_name_and_locale = {'versioned_object_id': {'$in': other_concepts_in_source},
                                    'names': {'$elemMatch': {'name': name.name, 'locale': name.locale}},
                                    'is_latest_version': True}

            if ConceptVersion.objects.raw_query(same_name_and_locale).count() > 0:
                raise ValidationError(validation_error)

    def short_name_cannot_be_marked_as_locale_preferred(self):
        short_preferred_names_in_concept = filter(
            lambda name: (name.is_short or name.is_search_index_term) and name.locale_preferred, self.concept.names)

        if len(short_preferred_names_in_concept) > 0:
            raise ValidationError({
                'names': [message_with_name_details(OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED,
                                                    short_preferred_names_in_concept[0])]
            })

    def all_non_short_names_must_be_unique(self):
        name_id = lambda n: n.locale + n.name

        non_short_names_in_concept = map(name_id, filter(lambda n: n.is_short == False, self.concept.names))
        name_set = set(non_short_names_in_concept)

        if len(name_set) != len(non_short_names_in_concept):
            raise ValidationError(
                {'names': [OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE]})

    def only_one_fully_specified_name_per_locale(self):
        fully_specified_names_per_locale = dict()

        for name in self.concept.names:
            if not name.is_fully_specified:
                continue

            if name.locale in fully_specified_names_per_locale:
                raise ValidationError(
                    {'names': [message_with_name_details(OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE, name)]})

            fully_specified_names_per_locale[name.locale] = True

    def no_more_than_one_short_name_per_locale(self):
        short_names_per_locale = dict()

        for name in self.concept.names:
            if not name.is_short:
                continue

            if name.locale in short_names_per_locale:
                raise ValidationError(
                    {'names': [message_with_name_details(OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE, name)]})

            short_names_per_locale[name.locale] = True

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

    def concept_class_should_be_valid_attribute(self, org):
        is_concept_class_valid = self.is_attribute_valid(self.concept.concept_class, org, 'Classes', 'Concept Class')

        if not is_concept_class_valid:
            raise ValidationError({'concept_class': [OPENMRS_CONCEPT_CLASS]})

    def data_type_should_be_valid_attribute(self, org):
        is_data_type_valid = self.is_attribute_valid(self.concept.datatype, org, 'Datatypes', 'Datatype')

        if not is_data_type_valid:
            raise ValidationError({'data_type': [OPENMRS_DATATYPE]})

    def name_type_should_be_valid_attribute(self, org):
        if not self.concept.names:
            return

        for name in self.concept.names:
            if name.type in ['FULLY_SPECIFIED', 'SHORT']:
                continue

            if self.is_attribute_valid(name.type, org, 'NameTypes', 'NameType'):
                continue

            raise ValidationError({'names': [message_with_name_details(OPENMRS_NAME_TYPE, name)]})

    def description_type_should_be_valid_attribute(self, org):
        if not self.concept.descriptions:
            return

        description_type_count = len(
            filter(lambda d: self.is_attribute_valid(d.type, org, 'DescriptionTypes', 'DescriptionType'),
                   self.concept.descriptions))

        if description_type_count < len(self.concept.descriptions):
            raise ValidationError({'descriptions': [OPENMRS_DESCRIPTION_TYPE]})

    def locale_should_be_valid_attribute(self, org):
        if not self.concept.names or not self.concept.descriptions:
            return

        name_locale_count = len(
            filter(lambda n: self.is_attribute_valid(n.locale, org, 'Locales', 'Locale'),
                   self.concept.names))

        if name_locale_count < len(self.concept.names):
            raise ValidationError({'names': [OPENMRS_NAME_LOCALE]})

        description_locale_count = len(
            filter(lambda d: self.is_attribute_valid(d.locale, org, 'Locales', 'Locale'),
                   self.concept.descriptions))

        if description_locale_count < len(self.concept.descriptions):
            raise ValidationError({'descriptions': [OPENMRS_DESCRIPTION_LOCALE]})

    def lookup_attributes_should_be_valid(self):
        if self.concept.concept_class in LOOKUP_CONCEPT_CLASSES:
            return

        from orgs.models import Organization
        ocl_org_filter = Organization.objects.filter(mnemonic='OCL')

        if ocl_org_filter.count() < 1:
            raise ValidationError({'non_field_errors': ['Lookup attributes must be imported']})

        org = ocl_org_filter.get()

        self.concept_class_should_be_valid_attribute(org)
        self.data_type_should_be_valid_attribute(org)
        self.name_type_should_be_valid_attribute(org)
        self.description_type_should_be_valid_attribute(org)
        self.locale_should_be_valid_attribute(org)
