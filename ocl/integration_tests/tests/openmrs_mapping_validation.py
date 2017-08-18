from django.core.urlresolvers import reverse

from mappings.tests import MappingBaseTest
from mappings.validation_messages import OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS, OPENMRS_INVALID_MAPTYPE
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import create_user, create_source, create_concept


class OpenMRSMappingCreateTest(MappingBaseTest):
    def test_create_mapping_duplicate_mapping_between_two_concepts(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        (concept1, _) = create_concept(user=self.user1, source=source)
        (concept2, _) = create_concept(user=self.user1, source=source)

        self.client.login(username='user1', password='user1')

        kwargs = {
            'source': source.mnemonic
        }
        mapping1 = {
            'from_concept_url': concept1.url,
            'to_concept_url': concept2.url,
            'map_type': 'Same As'

        }
        mapping2 = {
            'from_concept_url': concept1.url,
            'to_concept_url': concept2.url,
            'map_type': 'Narrower Than'

        }

        self.client.post(reverse('mapping-list', kwargs=kwargs), mapping1)
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), mapping2)

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {"errors": OPENMRS_SINGLE_MAPPING_BETWEEN_TWO_CONCEPTS})


    def test_create_mapping_maptype_without_found_lookup(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        (concept1, _) = create_concept(user=self.user1, source=source)
        (concept2, _) = create_concept(user=self.user1, source=source)

        self.client.login(username='user1', password='user1')

        kwargs = {
            'source': source.mnemonic
        }
        mapping = {
            'from_concept_url': concept1.url,
            'to_concept_url': concept2.url,
            'map_type': 'Wrong Map Type'

        }

        response = self.client.post(reverse('mapping-list', kwargs=kwargs), mapping)

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'errors': 'map_type : ' + OPENMRS_INVALID_MAPTYPE})