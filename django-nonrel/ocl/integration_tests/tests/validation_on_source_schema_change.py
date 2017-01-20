import json

from django.core.urlresolvers import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_200_OK

from concepts.tests import ConceptBaseTest
from concepts.validation_messages import OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE
from concepts.validators import message_with_name_details
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import create_source, create_user, create_localized_text, create_concept


class ValidationOnSourceSchemaTest(ConceptBaseTest):
    def test_change_source_schema_should_fail_when_not_valid_against_open_mrs(self):
        user = create_user()
        source_no_validation = create_source(user, organization=self.org1)

        non_unique_name = create_localized_text("Non Unique")

        concept_1, _ = create_concept(user, source_no_validation, mnemonic="concept1", names=[non_unique_name])
        concept_2, _ = create_concept(user, source_no_validation, mnemonic="concept2", names=[non_unique_name])

        self.client.login(username=user.username, password=user.password)

        kwargs = {'org': self.org1.mnemonic, 'source': source_no_validation.mnemonic}
        data = json.dumps({
            'custom_validation_schema': CUSTOM_VALIDATION_SCHEMA_OPENMRS
        })

        response = self.client.put(reverse('source-detail', kwargs=kwargs), data, content_type='application/json')

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(json.loads(response.content), {
            "failed_concept_validations": [
                {"mnemonic": concept_1.mnemonic,
                 "url": concept_1.url,
                 "errors": {"names": [
                     message_with_name_details(OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, non_unique_name)]}},
                {"mnemonic": concept_2.mnemonic,
                 "url": concept_2.url,
                 "errors": {"names": [
                     message_with_name_details(OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, non_unique_name)]}}]})


    def test_change_source_schema_should_fail_when_valid_against_open_mrs(self):
        user = create_user()
        source_no_validation = create_source(user, organization=self.org1)

        non_unique_name = create_localized_text("Non Unique")

        concept_1, _ = create_concept(user, source_no_validation, mnemonic="concept1", names=[create_localized_text("Name 1")])
        concept_2, _ = create_concept(user, source_no_validation, mnemonic="concept2", names=[create_localized_text("Name 2")])

        self.client.login(username=user.username, password=user.password)

        kwargs = {'org': self.org1.mnemonic, 'source': source_no_validation.mnemonic}
        data = json.dumps({
            'custom_validation_schema': CUSTOM_VALIDATION_SCHEMA_OPENMRS
        })

        response = self.client.put(reverse('source-detail', kwargs=kwargs), data, content_type='application/json')

        self.assertEqual(response.status_code, HTTP_200_OK)
