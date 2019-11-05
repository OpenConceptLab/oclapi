import requests
from users.models import UserProfile

from fhir.resources.fhirdate import FHIRDate
from fhir.resources.identifier import Identifier

from fhir.resources.codesystem import CodeSystem
from fhir.resources.codesystem import CodeSystemConcept

from fhir.resources.valueset import ValueSet
from fhir.resources.valueset import ValueSetCompose
from fhir.resources.valueset import ValueSetComposeInclude
from fhir.resources.valueset import ValueSetComposeIncludeConcept

from fhir.resources.conceptmap import ConceptMap
from fhir.resources.conceptmap import ConceptMapGroup
from fhir.resources.conceptmap import ConceptMapGroupElement
from fhir.resources.conceptmap import ConceptMapGroupElementTarget

__author__ = 'davetrig'


class BaseFhirMixin(object):
    def get_from_api(self, url):

        #profile = UserProfile.objects.get(mnemonic=username)
        #api_url = 'http://api.openconceptlab.org:8000'
        #api_token = profile.user.auth_token.key

        #api_url = 'http://api.openconceptlab.org:8000'
        api_url = 'http://localhost:8000'
        api_token = '891b4b17feab99f3ff7e5b5d04ccc5da7aa96da6'

        #api_url = 'https://api.staging.openconceptlab.org'
        #api_token = '57ce8e00f2461a844f428f92dafa26ce3ea0c115'

        ocl_api_headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token %s' % api_token
        }

        r = requests.get(api_url + url, headers=ocl_api_headers)
        r.raise_for_status()
        result = r.json()

        return result


class CodeSystemFhirMixin(BaseFhirMixin,):
    def build_from_dictionary(self, ocl_source):
        cs = CodeSystem()

        updated_date = ocl_source.get('updated_on')
        if (updated_date != None):
            date = FHIRDate(updated_date)
            cs.date = date

        extras = ocl_source.get('extras')
        oid = None
        if (extras != None):
            cs.title = extras.get('Title')
            cs.url = extras.get('uri')
            oid = extras.get('OID')

        cs.description = ocl_source.get('description')
        cs.experimental = False
        cs.id = ocl_source.get('id')
        cs.name = ocl_source.get('name')
        cs.publisher = ocl_source.get('owner')
        cs.status = 'active'

        if (oid != None):
            oid_identifier = Identifier()
            oid_identifier.system = "urn:ietf:rfc:3986"
            oid_identifier.value = "urn:oid:" + oid
            cs.identifier = []
            cs.identifier.append(oid_identifier)

        # content is required, but there is no value in OCL to use
        # valid values are not-present | example | fragment | complete | supplement
        cs.content = 'complete'

        url_concepts = ocl_source.get('concepts_url')
        if (url_concepts != None):
            concepts =  self.get_from_api(url_concepts)

            cs.concept = []
            for concept in concepts:
                cs_concept = CodeSystemConcept()
                cs_concept.code = concept.get('id')
                cs_concept.display = concept.get('display_name')
                cs.concept.append(cs_concept)

        return cs

class ValueSetFhirMixin(BaseFhirMixin,):
    def build_from_dictionary(self, ocl_collection):

        vs = ValueSet()

        updated_date = ocl_collection.get('updated_on')
        if (updated_date != None):
            date = FHIRDate(updated_date)
            vs.date = date

        extras = ocl_collection.get('extras')
        oid = None
        if (extras != None):
            vs.title = extras.get('Title')
            vs.url = extras.get('uri')
            oid = extras.get('OID')

        vs.description = ocl_collection.get('description')
        vs.experimental = False
        vs.id = ocl_collection.get('id')
        vs.name = ocl_collection.get('name')
        vs.publisher = ocl_collection.get('owner')
        vs.status = 'active'

        if (oid != None):
            oid_identifier = Identifier()
            oid_identifier.system = "urn:ietf:rfc:3986"
            oid_identifier.value = "urn:oid:" + oid
            vs.identifier = []
            vs.identifier.append(oid_identifier)

        compose = ValueSetCompose()
        compose.include = []

        url_concepts = ocl_collection.get('concepts_url')
        if (url_concepts != None):
            concepts = self.get_from_api(url_concepts)

            source_map = {}
            for concept in concepts:
                source_url = concept.get('owner_url') + 'sources/' + concept.get('source')
                if source_url not in source_map.keys():
                    source_map[source_url] = []

                include_concept = ValueSetComposeIncludeConcept()
                include_concept.code = concept.get('id')
                include_concept.display = concept.get('display_name')
                source_map[source_url].append(include_concept)

            for source_url in source_map.keys():
                source = self.get_from_api(source_url)
                compose_include = ValueSetComposeInclude()
                source_extras = source.get('extras')
                if (source_extras != None):
                    compose_include.system = source_extras.get('uri')
                compose_include.concept = source_map[source_url]
                compose.include.append(compose_include)

        vs.compose = compose

        # vs.contact
        # vs.contained
        # vs.copyright
        # vs.expansion
        # vs.extension
        # vs.identifier
        # vs.immutable
        # vs.implicitRules
        # vs.jurisdiction
        # vs.language
        # vs.meta
        # vs.modifierExtension
        # vs.purpose
        # vs.server
        # vs.text
        # vs.useContext
        # vs.version

        return vs

class ConceptMapFhirMixin(BaseFhirMixin,):
    def build_from_dictionary(self, ocl_conceptmap):
        source_system_url = None
        target_system_url = None
        mappings_url = ocl_conceptmap.get('mappings_url')

        cm = ConceptMap()

        updated_date = ocl_conceptmap.get('updated_on')
        if (updated_date != None):
            date = FHIRDate(updated_date)
            cm.date = date

        extras = ocl_conceptmap.get('extras')
        if (extras != None):
            source_system_url = extras.get('source_code_system')
            target_system_url = extras.get('target_code_system')


        cm.description = ocl_conceptmap.get('description')
        cm.experimental = False
        cm.id = ocl_conceptmap.get('id')
        cm.name = ocl_conceptmap.get('name')
        cm.publisher = ocl_conceptmap.get('owner')
        cm.status = 'active'
        cm.title = ocl_conceptmap.get('full_name')

        cm.sourceUri = source_system_url
        cm.targetUri = target_system_url

        if (mappings_url != None):
            mappings = self.get_from_api(mappings_url)

            if (mappings != None):
                group = ConceptMapGroup()
                group.source = source_system_url
                group.target = target_system_url
                group_elements = []

                for mapping in mappings:
                    e = ConceptMapGroupElement()
                    e.id = mapping.get('id')

                    e.code = mapping.get('from_concept_code')
                    e.display = mapping.get('from_concept_name')

                    t = ConceptMapGroupElementTarget()
                    t.code = mapping.get('to_concept_code')
                    t.display = mapping.get('to_concept_name')
                    t.equivalence = get_equivalence(mapping.get('map_type'))

                    e.target = [t]

                    group_elements.append(e)

                group.element = group_elements
                cm.group = [group]

        return cm


def get_equivalence(map_type):

    if (map_type == 'Same As'):
        return 'equivalent'
    #
    # Put other value translations here
    #
    # default to 'relatedto'? Guess on my part - DT
    else:
        return 'relatedto'
