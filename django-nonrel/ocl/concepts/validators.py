import logging

from django.core.cache import cache
from django.core.exceptions import ValidationError

from concepts.validation_messages import  BASIC_DESCRIPTION_CANNOT_BE_EMPTY, BASIC_NAMES_CANNOT_BE_EMPTY
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS

logger = logging.getLogger('oclapi')


def message_with_name_details(message, name):
    if name is None:
        return message

    name_str = name.name or 'n/a'
    locale = name.locale or 'n/a'
    preferred = 'yes' if name.locale_preferred else 'no'
    return unicode(u'{}: {} (locale: {}, preferred: {})'.format(message, unicode(name_str), locale, preferred))

class ValidatorSpecifier:
    def __init__(self):
        from concepts.custom_validators import OpenMRSConceptValidator
        self.validator_map = {
            CUSTOM_VALIDATION_SCHEMA_OPENMRS: OpenMRSConceptValidator
        }
        self.reference_values = dict()
        self.name_registry = dict()

    def with_validation_schema(self, schema):
        self.validation_schema = schema
        return self

    def with_repo(self, repo):
        from concepts.models import Concept
        concepts_in_source = Concept.objects.filter(parent_id=repo.id, is_active=True, retired=False).all()

        name_registry = dict()

        for concept in concepts_in_source:
            for name in concept.names:
                if name.is_short:
                    continue
                name_key = u"{}{}".format(name.locale, name.name)
                ids = name_registry.get(name_key, [])
                ids.append(concept.id)
                name_registry[name_key] = ids

        self.name_registry = name_registry

        return self

    def with_reference_values(self):
        from orgs.models import Organization
        from sources.models import Source

        FIVE_MINS = 5*60
        reference_value_source_mnemonics = ['Classes', 'Datatypes', 'NameTypes', 'DescriptionTypes', 'Locales']

        ocl_org_filter = Organization.objects.get(mnemonic='OCL')

        if not cache.has_key('reference_sources'):
            cache.set('reference_sources', Source.objects.filter(parent_id=ocl_org_filter.id, mnemonic__in=reference_value_source_mnemonics), FIVE_MINS)

        sources = cache.get('reference_sources')

        self.reference_values = dict()
        for source in sources:
            if not cache.has_key(source.mnemonic):
                cache.set(source.mnemonic,self._get_reference_values(source), FIVE_MINS)
            reference_values = cache.get(source.mnemonic)
            self.reference_values[source.mnemonic] = reference_values

        return self

    def _get_reference_values(self, reference_value_source):
        from concepts.models import Concept
        reference_concepts = list(Concept.objects.filter(retired=False, is_active=True, parent_id=reference_value_source.id).all())
        names_in_concepts = map(lambda value: value.names, reference_concepts)
        return [name_object.name for names in names_in_concepts for name_object in names]

    def get(self):
        validator_class = self.validator_map.get(self.validation_schema, BasicConceptValidator)

        kwargs = {
            'name_registry': self.name_registry,
            'reference_values': self.reference_values
        }

        return validator_class(**kwargs)



class BaseConceptValidator:
    def __init__(self, **kwargs):
        pass

    def validate(self, concept):
        self.validate_concept_based(concept)
        self.validate_source_based(concept)

    def validate_concept_based(self, concept):
        pass

    def validate_source_based(self, concept):
        pass

class BasicConceptValidator(BaseConceptValidator):

    def validate_concept_based(self, concept):
        self.description_cannot_be_null(concept)
        self.must_have_at_least_one_name(concept)
        self.custom_attribute_key_must_be_encoded(concept)


    def validate_source_based(self, concept):
        pass

    def must_have_at_least_one_name(self, concept):
        if concept.names and len(concept.names) > 0:
            return

        raise ValidationError({'names': [BASIC_NAMES_CANNOT_BE_EMPTY]})

    def description_cannot_be_null(self, concept):
        if not concept.descriptions:
            return

        if len(concept.descriptions) == 0:
            return

        empty_descriptions = filter((lambda description: (not description.name) or (description.name == "")), concept.descriptions)

        if len(empty_descriptions):
            raise ValidationError({'descriptions': [BASIC_DESCRIPTION_CANNOT_BE_EMPTY]})

    def custom_attribute_key_must_be_encoded(self, concept):
        concept.encode_extras()
        return

