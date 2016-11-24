from django.core.exceptions import ValidationError


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

            if preferred_name_locales_in_concept.has_key(name.locale):
                raise ValidationError({
                    'names': ['A concept may not have more than one preferred name (per locale)']
                })

            preferred_name_locales_in_concept[name.locale] = True

    def must_have_unique_fully_specified_name_for_same_source_and_locale(self):
        for name in self.concept.names:
            if not name.is_fully_specified:
                continue

            raw_query = {'parent_id': self.concept.parent_source.id, 'names.name': name.name,
                         'names.locale': name.locale,
                         'names.type': name.type}

            # TODO find a better solution for circular dependency
            from concepts.models import Concept
            if Concept.objects.raw_query(raw_query).count() > 0:
                raise ValidationError({
                    'names': [
                        'Custom validation rules require fully specified name should be unique for same locale and source']
                })

    def short_name_cannot_be_marked_as_locale_preferred(self):
        short_preferred_names_in_concept = filter(
            lambda name: (name.is_short or name.is_search_index_term) and name.locale_preferred, self.concept.names)

        if len(short_preferred_names_in_concept) > 0:
            raise ValidationError({
                'names': ['A short name cannot be marked as locale preferred']
            })

    def all_non_short_names_must_be_unique(self):
        name_id = lambda n: n.locale + n.name

        non_short_names_in_concept = map(name_id, filter(lambda n: n.is_short == False, self.concept.names))
        name_set = set(non_short_names_in_concept)

        if len(name_set) != len(non_short_names_in_concept):
            raise ValidationError(
                {'names': ['All names except short names must unique for a concept and locale']})

    def only_one_fully_specified_name_per_locale(self):
        fully_specified_names_per_locale = dict()

        for name in self.concept.names:
            if not name.is_fully_specified:
                continue

            if fully_specified_names_per_locale.has_key(name.locale):
                raise ValidationError(
                    {'names': ['A concept may not have more than one fully specified name in any locale']})

            fully_specified_names_per_locale[name.locale] = True

    def no_more_than_one_short_name_per_locale(self):
        short_names_per_locale = dict()

        for name in self.concept.names:
            if not name.is_short:
                continue

            if short_names_per_locale.has_key(name.locale):
                raise ValidationError(
                    {'names': ['A concept cannot have more than one short name in a locale']})

            short_names_per_locale[name.locale] = True
