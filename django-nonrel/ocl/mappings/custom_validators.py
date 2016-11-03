from django.core.exceptions import ValidationError

class OpenMRSMappingValidator:
    def __init__(self, concept):
        self.concept = concept

    def validate(self):
        self.pair_must_be_unique()

    def pair_must_be_unique(self):
        raise ValidationError("asdfasdf")

        # preferred_name_locales_in_concept = dict()
        #
        # for name in self.concept.names:
        #     if not name.locale_preferred:
        #         continue
        #
        #     if preferred_name_locales_in_concept.has_key(name.locale):
        #         raise ValidationError({
        #             'names': ['Custom validation rules require a concept to have exactly one preferred name']
        #         })
        #
        #     preferred_name_locales_in_concept[name.locale] = True
        #
        #
        #
        # for name in self.concept.names:
        #     if not name.is_fully_specified:
        #         continue
        #
        #     raw_query = {'parent_id': self.concept.parent_source.id, 'names.name': name.name, 'names.locale': name.locale,
        #                  'names.type': name.type}
        #
        #     # TODO find a better solution for circular dependency
        #     from concepts.models import Concept
        #     if Concept.objects.raw_query(raw_query).count() > 0:
        #         raise ValidationError({
        #             'names': ['Custom validation rules require fully specified name should be unique for same locale and source']
        #         })


