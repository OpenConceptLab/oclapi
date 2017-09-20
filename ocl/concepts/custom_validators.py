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
    def __init__(self, **kwargs):
        self.repo = kwargs.pop('repo')
        self.reference_values = kwargs.pop('reference_values')

    def validate_concept_based(self, concept):
        self.must_have_exactly_one_preferred_name(concept)
        self.all_non_short_names_must_be_unique(concept)
        self.no_more_than_one_short_name_per_locale(concept)
        self.short_name_cannot_be_marked_as_locale_preferred(concept)
        self.only_one_fully_specified_name_per_locale(concept)
        self.requires_at_least_one_fully_specified_name(concept)
        self.lookup_attributes_should_be_valid(concept)

    def validate_source_based(self, concept):
        self.fully_specified_name_should_be_unique_for_source_and_locale(concept)
        self.preferred_name_should_be_unique_for_source_and_locale(concept)

    def must_have_exactly_one_preferred_name(self, concept):
        preferred_name_locales_in_concept = dict()

        for name in concept.names:
            if not name.locale_preferred:
                continue

            if name.locale in preferred_name_locales_in_concept:
                raise ValidationError({
                    'names': [message_with_name_details(OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, name)]
                })

            preferred_name_locales_in_concept[name.locale] = True

    def requires_at_least_one_fully_specified_name(self, concept):
        # A concept must have at least one fully specified name (across all locales)
        fully_specified_name_count = len(
            filter(lambda n: n.is_fully_specified, concept.names))
        if fully_specified_name_count < 1:
            raise ValidationError({'names': [OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME]})

    def preferred_name_should_be_unique_for_source_and_locale(self, concept):
        self.attribute_should_be_unique_for_source_and_locale(concept, attribute='locale_preferred',
                                                              error_message=OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE)

    def fully_specified_name_should_be_unique_for_source_and_locale(self, concept):
        self.attribute_should_be_unique_for_source_and_locale(concept, attribute='is_fully_specified',
                                                              error_message=OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE)

    def attribute_should_be_unique_for_source_and_locale(self, concept, attribute, error_message):
        self_id = getattr(concept, 'versioned_object_id', getattr(concept, 'id', None))

        names = [n for n in concept.names if getattr(n, attribute)]
        for name in names:
            if self.no_other_record_has_same_name(name, self_id):
                continue

            raise ValidationError({
                'names': [message_with_name_details(error_message, name)]})

    def no_other_record_has_same_name(self, name, self_id):
        if not self.repo:
            return True

        from concepts.models import Concept
        from django_mongodb_engine.query import A
        conceptsQuery = Concept.objects.filter(parent_id=self.repo.id, is_active=True, retired=False, names=A('name', name.name)).filter(
            names=A('locale', name.locale)).exclude(id=self_id)

        concepts = conceptsQuery.exclude(names=A('type', 'SHORT'))
        if concepts:
            #Could not get it to work with one query with 2 'A' excludes for names thus querying twice
            concepts = conceptsQuery.exclude(names=A('type', 'Short'))

        isEmpty = not concepts

        return isEmpty

    def short_name_cannot_be_marked_as_locale_preferred(self, concept):
        short_preferred_names_in_concept = filter(
            lambda name: (name.is_short or name.is_search_index_term) and name.locale_preferred, concept.names)

        if len(short_preferred_names_in_concept) > 0:
            raise ValidationError({
                'names': [message_with_name_details(OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED,
                                                    short_preferred_names_in_concept[0])]
            })

    def all_non_short_names_must_be_unique(self, concept):
        name_id = lambda n: n.locale + n.name

        non_short_names_in_concept = map(name_id, filter(lambda n: n.is_short == False, concept.names))
        name_set = set(non_short_names_in_concept)

        if len(name_set) != len(non_short_names_in_concept):
            raise ValidationError(
                {'names': [OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE]})

    def only_one_fully_specified_name_per_locale(self, concept):
        fully_specified_names_per_locale = dict()

        for name in concept.names:
            if not name.is_fully_specified:
                continue

            if name.locale in fully_specified_names_per_locale:
                raise ValidationError(
                    {'names': [message_with_name_details(OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE, name)]})

            fully_specified_names_per_locale[name.locale] = True

    def no_more_than_one_short_name_per_locale(self, concept):
        short_names_per_locale = dict()

        for name in concept.names:
            if not name.is_short:
                continue

            if name.locale in short_names_per_locale:
                raise ValidationError(
                    {'names': [message_with_name_details(OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE, name)]})

            short_names_per_locale[name.locale] = True

    def concept_class_should_be_valid_attribute(self, concept):
        if concept.concept_class not in self.reference_values['Classes']:
            raise ValidationError({'concept_class': [OPENMRS_CONCEPT_CLASS]})

    def data_type_should_be_valid_attribute(self, concept):
        if (concept.datatype or 'None') not in self.reference_values['Datatypes']:
            raise ValidationError({'data_type': [OPENMRS_DATATYPE]})

    def name_type_should_be_valid_attribute(self, concept):
        if not concept.names:
            return

        for name in concept.names:
            if name.type in ['FULLY_SPECIFIED', 'SHORT']:
                continue

            if (name.type or 'None') in self.reference_values['NameTypes']:
                continue

            raise ValidationError({'names': [message_with_name_details(OPENMRS_NAME_TYPE, name)]})

    def description_type_should_be_valid_attribute(self, concept):
        if not concept.descriptions:
            return

        for description in concept.descriptions:
            if (description.type or 'None') not in self.reference_values['DescriptionTypes']:
                raise ValidationError({'descriptions': [OPENMRS_DESCRIPTION_TYPE]})

    def locale_should_be_valid_attribute(self, concept):
        if not concept.names or not concept.descriptions:
            return

        for name in concept.names:
            if name.locale not in self.reference_values['Locales']:
                raise ValidationError({'names': [OPENMRS_NAME_LOCALE]})

        for description in concept.descriptions:
            if description.locale not in self.reference_values['Locales']:
                raise ValidationError({'descriptions': [OPENMRS_DESCRIPTION_LOCALE]})

    def lookup_attributes_should_be_valid(self, concept):
        if concept.concept_class in LOOKUP_CONCEPT_CLASSES:
            return

        self.concept_class_should_be_valid_attribute(concept)
        self.data_type_should_be_valid_attribute(concept)
        self.name_type_should_be_valid_attribute(concept)
        self.description_type_should_be_valid_attribute(concept)
        self.locale_should_be_valid_attribute(concept)
