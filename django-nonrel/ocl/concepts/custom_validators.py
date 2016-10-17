from django.core.exceptions import ValidationError


class OpenMRSConceptValidator():
    def __init__(self, concept):
        self.concept = concept

    def validate(self):
        self.must_have_exactly_one_preferred_name()
        self.preferred_name_should_be_different_than_index_term()
        self.all_non_short_names_must_be_unique()

    def must_have_exactly_one_preferred_name(self):
        preferred_name_locales_in_concept = dict()

        for name in self.concept.names:
            if not name.locale_preferred:
                continue

            if preferred_name_locales_in_concept.has_key(name.locale):
                raise ValidationError({
                    'names': ['Custom validation rules require a concept to have exactly one preferred name']
                })

            preferred_name_locales_in_concept[name.locale] = True

    def preferred_name_should_be_different_than_index_term(self):
        preferred_names_in_concept = map(lambda no: no.name, filter(lambda n: n.locale_preferred, self.concept.names))

        if len(filter(lambda n: n.type == "INDEX_TERM" and n.locale_preferred == True, self.concept.names)) > 0:
            raise ValidationError({
                'names': ['Custom validation rules require a preferred name not to be an index/search term']
            })

        short_names_in_concept = map(lambda no: no.name, filter(lambda n: n.type == "SHORT", self.concept.names))

        if set(preferred_names_in_concept).intersection(short_names_in_concept):
            raise ValidationError({
                'names': ['Custom validation rules require a preferred name to be different than a short name']
            })

    def all_non_short_names_must_be_unique(self):
        name_id = lambda n: n.locale + n.name

        non_short_names_in_concept = map(name_id, filter(lambda n: n.type != "SHORT", self.concept.names))
        name_set = set(non_short_names_in_concept)

        if len(name_set) != len(non_short_names_in_concept):
            raise ValidationError(
                {'names': ['Custom validation rules require all names except type=SHORT to be unique']})
