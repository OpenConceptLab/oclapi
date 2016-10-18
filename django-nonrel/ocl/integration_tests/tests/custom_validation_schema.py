from concepts.tests import ConceptBaseTest
from test_helper.base import create_user, create_source
from sources.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from rest_framework import status
from django.core.urlresolvers import reverse
import json

class OpenMRSConceptCreateTest(ConceptBaseTest):
    def test_create_concept_without_description(self):
        user = create_user()

        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS, organization=self.org1)

        self.client.login(username=user.username, password=user.password)

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source_with_open_mrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "conceptclass",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }]
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)