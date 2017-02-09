import json

from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.reverse import reverse

from collection.validation_messages import HEAD_OF_CONCEPT_ADDED_TO_COLLECTION, CONCEPT_ADDED_TO_COLLECTION_FMT, \
    HEAD_OF_MAPPING_ADDED_TO_COLLECTION, MAPPING_ADDED_TO_COLLECTION_FMT, REFERENCE_ALREADY_EXISTS, CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE, \
    CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE
from collection.models import Collection
from concepts.models import ConceptVersion
from concepts.tests import ConceptBaseTest, create_localized_text
from mappings.models import MappingVersion, Mapping
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import create_source, create_user, create_concept, create_collection, create_mapping


class AddCollectionReferenceAPITest(ConceptBaseTest):
    def test_add_concept_without_version_information_should_return_info_and_versioned_reference(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept, errors) = create_concept(mnemonic='concept12', user=user, source=source_with_open_mrs)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        data = json.dumps({
            'data': {
                'expressions': [concept.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')
        updated_collection = Collection.objects.get(mnemonic=collection.name)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': True, 'expression': updated_collection.current_references()[0],
                            'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION}])

    def test_add_concept_with_version_information_should_return_success_info_and_same_references(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept, errors) = create_concept(mnemonic='concept12', user=user, source=source_with_open_mrs)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        data = json.dumps({
            'data': {
                'expressions': [concept.get_latest_version.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')
        updated_collection = Collection.objects.get(mnemonic=collection.name)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': True, 'expression': updated_collection.current_references()[0],
                            'message': CONCEPT_ADDED_TO_COLLECTION_FMT.format(concept.mnemonic, collection.name)}])

    def test_add_mapping_without_version_information_should_return_info_and_versioned_reference(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'expressions': [mapping.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')
        updated_collection = Collection.objects.get(mnemonic=collection.name)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': True, 'expression': updated_collection.current_references()[0],
                            'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}])

    def create_source_and_user_fixture(self):
        user = create_user()
        source_with_open_mrs = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                             organization=self.org1)
        self.client.login(username=user.username, password=user.password)
        return source_with_open_mrs, user

    def test_add_mapping_with_version_information_should_return_info_and_same_reference(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, _) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, _) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        data = json.dumps({
            'data': {
                'expressions': [mapping.get_latest_version.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')
        updated_collection = Collection.objects.get(mnemonic=collection.name)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': True, 'expression': updated_collection.current_references()[0],
                            'message': MAPPING_ADDED_TO_COLLECTION_FMT.format(mapping.mnemonic, collection.name)}])

    def test_add_resources_with_api_should_return_info_and_versioned_references(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        data = json.dumps({
            'data': {
                'expressions': [concept_one.url, concept_two.get_latest_version.url, mapping.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data,
                              [{'added': True, 'expression': concept_one.get_latest_version.url,
                                'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                               {'added': True, 'expression': concept_two.get_latest_version.url,
                                'message': CONCEPT_ADDED_TO_COLLECTION_FMT.format(concept_two.mnemonic, collection.name)},
                               {'added': True, 'expression': mapping.get_latest_version.url,
                                'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}])

    def test_add_resources_with_api_should_return_info_and_errors_and_versioned_references(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        invalid_reference = concept_one.url.replace('concepts', 'mappings')

        data = json.dumps({
            'data': {
                'expressions': [concept_one.url, invalid_reference, mapping.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data,
                              [{'added': True, 'expression': concept_one.get_latest_version.url,
                                'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                               {'added': False, 'expression': invalid_reference,
                                'message': ['Expression specified is not valid.']},
                               {'added': True, 'expression': mapping.get_latest_version.url,
                                'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}])

    def test_add_duplicate_concept_expressions_should_fail(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept, _) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'expressions': [concept.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}
        self.client.put(reverse('collection-references', kwargs=kwargs), data,
                        content_type='application/json')

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': False, 'expression': unicode(concept.url),
                            'message': [REFERENCE_ALREADY_EXISTS]},
                           ])

    def test_add_duplicate_mapping_expressions_should_fail(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic="ConceptOne", user=self.user1, source=source_with_open_mrs, names=[
            create_localized_text(name='UserOne', locale='es', type='FULLY_SPECIFIED')])
        (concept_two, errors) = create_concept(mnemonic="ConceptTwo", user=self.user1, source=source_with_open_mrs, names=[
            create_localized_text(name='UserTwo', locale='en', type='FULLY_SPECIFIED')])

        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'mappings': [mapping.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        self.client.put(reverse('collection-references', kwargs=kwargs), data,
                        content_type='application/json')

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': False, 'expression': mapping.url,
                            'message': [REFERENCE_ALREADY_EXISTS]}])

    def test_add_duplicate_concept_reference_different_version_number(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(mnemonic="ConceptOne", user=self.user1, source=source_with_open_mrs, names=[
            create_localized_text(name='UserOne', locale='es', type='FULLY_SPECIFIED')])

        data = json.dumps({
            'data': {
                'expressions': [concept_one.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        self.client.put(reverse('collection-references', kwargs=kwargs), data,
                        content_type='application/json')

        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=concept_one,
            concept_class='Diagnosis',
            datatype=concept_one.datatype,
            names=concept_one.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")])

        concept_version.full_clean()
        concept_version.save()

        data = json.dumps({
            'data': {
                'expressions': [concept_version.url]
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, [{'added': False, 'expression': concept_version.url,
                                           'message': [REFERENCE_ALREADY_EXISTS]}])

    def test_add_duplicate_mapping_reference_different_version_number(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(mnemonic="ConceptOne", user=self.user1, source=source_with_open_mrs, names=[
            create_localized_text(name='UserOne', locale='es', type='FULLY_SPECIFIED')])

        (concept_two, errors) = create_concept(mnemonic="ConceptTwo", user=self.user1, source=source_with_open_mrs, names=[
            create_localized_text(name='UserTwo', locale='en', type='FULLY_SPECIFIED')])

        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)

        kwargs = {'user': user.username, 'collection': collection.name}

        data = json.dumps({
            'data': {
                'expressions': [mapping.url]
            }
        })

        self.client.put(reverse('collection-references', kwargs=kwargs), data,
                        content_type='application/json')

        mapping_version = MappingVersion(
            created_by=self.user1,
            updated_by=self.user1,
            map_type=mapping.map_type,
            parent=source_with_open_mrs,
            from_concept=concept_two,
            to_concept=concept_one,
            external_id='mapping1',
            versioned_object_id=mapping.id,
            versioned_object_type=ContentType.objects.get_for_model(Mapping),
            mnemonic='1'
        )

        mapping_version.full_clean()
        mapping_version.save()

        data = json.dumps({
            'data': {
                'expressions': [mapping_version.url]
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, [{'added': False, 'expression': mapping_version.url,
                                           'message': [REFERENCE_ALREADY_EXISTS]}])

    def test_add_concept_as_single_reference_without_version_information_should_add_latest_version_number(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'expressions': [concept.url]
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.assertEquals(response.data,
                          [{'added': True, 'expression': concept.get_latest_version.url,
                            'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION}])

    def test_add_concept_as_multiple_reference_without_version_information_should_add_latest_versions_numbers(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'concepts': [concept_one.url, concept_two.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data,
                              [{'added': True, 'expression': concept_one.get_latest_version.url,
                                'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                               {'added': True, 'expression': concept_two.get_latest_version.url,
                                'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION}])

    def test_add_mapping_as_single_reference_without_version_information_should_add_latest_version_number(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'mappings': [mapping.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': True, 'expression': mapping.get_latest_version.url,
                            'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}])

    def test_add_mapping_as_multiple_reference_without_version_information_should_add_latest_versions_numbers(self):
        source_with_open_mrs, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(mnemonic='conceptTwo', user=user, source=source_with_open_mrs)
        (concept_two, errors) = create_concept(mnemonic='conceptOne', user=user, source=source_with_open_mrs)
        mapping_one = create_mapping(user, source_with_open_mrs, concept_one, concept_two)
        mapping_two = create_mapping(user, source_with_open_mrs, concept_two, concept_one)
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'mappings': [mapping_one.url, mapping_two.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data,
                              [{'added': True, 'expression': mapping_one.get_latest_version.url,
                                'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION},
                               {'added': True, 'expression': mapping_two.get_latest_version.url,
                                'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}])

    def test_concept_fully_specified_name_within_collection_should_be_unique(self):
        source_with_open_mrs_one, user = self.create_source_and_user_fixture()
        source_with_open_mrs_two, user = self.create_source_and_user_fixture()
        (concept_one, errors) = create_concept(user=self.user1, source=source_with_open_mrs_one, names=[
            create_localized_text(name='Non Unique Name', locale='en', type='FULLY_SPECIFIED')])
        (concept_two, errors) = create_concept(user=self.user1, source=source_with_open_mrs_two, names=[
            create_localized_text(name='Non Unique Name', locale='en', type='FULLY_SPECIFIED')])

        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'concepts': [concept_one.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        self.client.put(reverse('collection-references', kwargs=kwargs), data,
                        content_type='application/json')

        data = json.dumps({
            'data': {
                'concepts': [concept_two.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data,
                          [{'added': False, 'expression': concept_two.url,
                            'message': [CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE]}
                           ])

    def test_preferred_name_within_collection_should_be_unique(self):
        source_with_open_mrs_one, user = self.create_source_and_user_fixture()
        source_with_open_mrs_two, user = self.create_source_and_user_fixture()

        (concept_one, errors) = create_concept(user=self.user1, source=source_with_open_mrs_one, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name', locale='en', type='Fully Specified')
        ])

        (concept_two, errors) = create_concept(user=self.user1, source=source_with_open_mrs_two, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name 2', locale='en', type='Fully Specified')
        ])

        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        data = json.dumps({
            'data': {
                'concepts': [concept_one.url],
            }
        })

        kwargs = {'user': user.username, 'collection': collection.name}

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, [{'added': True, 'expression': concept_one.get_latest_version.url,
                                           'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION}])

        data = json.dumps({
            'data': {
                'concepts': [concept_two.url],
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, [{'added': False, 'expression': concept_two.url,
                                           'message': [CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE]}])

    def test_when_add_concept_as_a_reference_should_add_related_mappings(self):
        source, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (from_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name', locale='en', type='Fully Specified')
        ])

        (to_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name 2', locale='en', type='Fully Specified')
        ])

        mapping = create_mapping(user, source, from_concept, to_concept)

        kwargs = {'user': user.username, 'collection': collection.name}

        data = json.dumps({
            'data': {
                'expressions': [from_concept.url],
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data, [{'added': True, 'expression': from_concept.get_latest_version.url,
                                               'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                                              {'added': True, 'expression': mapping.get_latest_version.url,
                                               'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}
                                              ])

    def test_when_add_concept_as_a_reference_should_add_multiple_related_mappings(self):
        source, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (from_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')
        ])

        (to_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='None')
        ])

        (to_concept2, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='fr', type='FULLY_SPECIFIED')
        ])

        mapping = create_mapping(user, source, from_concept, to_concept)

        mapping2 = create_mapping(user, source, from_concept, to_concept2)

        kwargs = {'user': user.username, 'collection': collection.name}

        data = json.dumps({
            'data': {
                'expressions': [from_concept.url],
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        expected_response = [{'added': True, 'expression': from_concept.get_latest_version.url, 'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                             {'added': True, 'expression': mapping.get_latest_version.url, 'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION},
                             {'added': True, 'expression': mapping2.get_latest_version.url, 'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}]

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data, expected_response)

    def test_when_add_concept_as_a_reference_and_has_not_related_mappings_should_add_only_concept(self):
        source, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (from_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')
        ])

        (to_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='None')
        ])

        (from_concept2, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User1', locale='fr', type='FULLY_SPECIFIED')
        ])

        non_related_mapping = create_mapping(user, source, from_concept2, to_concept)

        kwargs = {'user': user.username, 'collection': collection.name}

        data = json.dumps({
            'data': {
                'expressions': [from_concept.url],
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data, [{'added': True, 'expression': from_concept.get_latest_version.url, 'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION}])
        self.assertEquals(len(response.data), 1)

    def test_when_add_concept_with_related_mappings_as_a_reference_and_same_mapping(self):
        source, user = self.create_source_and_user_fixture()
        collection = create_collection(user, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (from_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name', locale='en', type='Fully Specified')
        ])

        (to_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name 2', locale='en', type='Fully Specified')
        ])

        mapping = create_mapping(user, source, from_concept, to_concept)

        kwargs = {'user': user.username, 'collection': collection.name}

        data = json.dumps({
            'data': {
                'expressions': [from_concept.url, mapping.url],
            }
        })

        response = self.client.put(reverse('collection-references', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data, [{'added': True, 'expression': from_concept.get_latest_version.url,
                                               'message': HEAD_OF_CONCEPT_ADDED_TO_COLLECTION},
                                              {'added': True, 'expression': mapping.get_latest_version.url,
                                               'message': HEAD_OF_MAPPING_ADDED_TO_COLLECTION}
                                              ])
        self.assertEquals(len(response.data), 2)
