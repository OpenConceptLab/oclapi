from django.core.exceptions import ValidationError

from concepts.validation_messages import OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE, \
    OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE, OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE, \
    OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, \
    OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED


class OpenMRSConceptValidator:
    def __init__(self, concept):
        self.concept = concept

    def validate_concept_based(self):
        self.must_have_exactly_one_preferred_name()
        self.all_non_short_names_must_be_unique()
        self.no_more_than_one_short_name_per_locale()
        self.short_name_cannot_be_marked_as_locale_preferred()
        self.only_one_fully_specified_name_per_locale()

    def validate_source_based(self):
        self.must_have_unique_fully_specified_name_for_same_source_and_locale()

    def must_have_exactly_one_preferred_name(self):
        preferred_name_locales_in_concept = dict()

        for name in self.concept.names:
            if not name.locale_preferred:
                continue

            if name.locale in preferred_name_locales_in_concept:
                raise ValidationError({
                    'names': [OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME]
                })

            preferred_name_locales_in_concept[name.locale] = True

    def must_have_unique_fully_specified_name_for_same_source_and_locale(self):
        from concepts.models import Concept, ConceptVersion

        # Concept preferred_name should be unique for same source and locale.
        validation_error = {'names': [
            OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE]}
        fully_specified_names_in_concept = dict()
        self_id = getattr(self.concept, "versioned_object_id", None)

        for name in [n for n in self.concept.names if n.is_fully_specified]:
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
                'names': [OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED]
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
                    {'names': [OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE]})

            fully_specified_names_per_locale[name.locale] = True

    def no_more_than_one_short_name_per_locale(self):
        short_names_per_locale = dict()

        for name in self.concept.names:
            if not name.is_short:
                continue

            if name.locale in short_names_per_locale:
                raise ValidationError(
                    {'names': [OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE]})

            short_names_per_locale[name.locale] = True
