from concepts.tests import ConceptBaseTest
from test_helper.base import create_user, create_source
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from rest_framework import status
from django.core.urlresolvers import reverse
import json


def open_mrs_concept_template(update=None):
    template = {
        "id": "12399000",
        "concept_class": "Diagnosis",
        "names": [{
            "name": "grip",
            "locale": 'en',
            "name_type": "Short"
        }, {
            "name": "grip2",
            "locale": 'en',
            "name_type": "FULLY_SPECIFIED",
            "locale_preferred": True

        }],
        "descriptions": [
            {"description": "description", "locale": "en", "description_type": "None"}
        ],
        "datatype": "None"}

    if update:
        template.update(update)

    return template

def underscore_concept_template(update=None):
    template = {
        "id": "My_Underscore_Concept",
        "concept_class": "Diagnosis",
        "names": [{
            "name": "Underscore Concept",
            "locale": 'en',
            "name_type": "Short"
        }, {
            "name": "My Underscore Concept (FS)",
            "locale": 'en',
            "name_type": "FULLY_SPECIFIED",
            "locale_preferred": True

        }],
        "descriptions": [
            {"description": "description", "locale": "en", "description_type": "None"}
        ],
        "datatype": "None"}

    if update:
        template.update(update)

    return template


class OpenMRSConceptCreateTest(ConceptBaseTest):
    def test_concept_should_have_exactly_one_preferred_name_per_locale_positive(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template())

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_concept_id_should_allow_underscore_positive(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(underscore_concept_template())

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_concept_should_have_exactly_one_preferred_name_per_locale_negative(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED",
                    "locale_preferred": True
                }, {
                    "name": "grip2",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED",
                    "locale_preferred": True

                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concepts_should_have_unique_fully_specified_name_per_locale_positive(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template())

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_concepts_should_have_unique_fully_specified_name_per_locale_negative(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }, {
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concepts_should_have_unique_fully_specified_name_per_source_locale_negative(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data_valid = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data_valid, content_type='application/json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        data_invalid = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data_valid,
                                    content_type='application/json')
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_preferred_name_cannot_be_short_negative(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "SHORT",
                    "locale_preferred": True
                }, {
                    "name": "grip2",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"

                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preferred_name_cannot_be_index_term(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "INDEX_TERM",
                    "locale_preferred": True
                }, {
                    "name": "grip2",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"

                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_name_should_be_unique_unless_short_term_positive(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "SHORT"
                }, {
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_name_should_be_unique_unless_short_term_negative(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        kwargs = {'org': self.org1.mnemonic, 'source': source_with_open_mrs.mnemonic}
        data = json.dumps(open_mrs_concept_template(
            {"names":
                [{
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "INDEX_TERM"
                }, {
                    "name": "grip",
                    "locale": 'en',
                    "name_type": "FULLY_SPECIFIED"
                }]
            }
        ))

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
