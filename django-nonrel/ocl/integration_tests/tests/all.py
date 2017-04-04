import json
from urlparse import urlparse

from django.core.urlresolvers import reverse
from django.test import Client
from django.test.client import MULTIPART_CONTENT, FakePayload
from django.utils.encoding import force_str
from django.utils.unittest.case import skip
from haystack.management.commands import update_index
from moto import mock_s3
from rest_framework import status

from collection.models import Collection, CollectionVersion
from collection.tests import CollectionBaseTest
from concepts.models import Concept, LocalizedText, ConceptVersion
from concepts.tests import ConceptBaseTest
from concepts.validation_messages import OPENMRS_DESCRIPTION_TYPE, OPENMRS_NAME_TYPE, OPENMRS_DATATYPE, OPENMRS_CONCEPT_CLASS, \
    BASIC_NAMES_CANNOT_BE_EMPTY
from mappings.models import Mapping, MappingVersion
from mappings.tests import MappingBaseTest
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_NONE, LOOKUP_CONCEPT_CLASSES
from sources.models import Source, SourceVersion
from sources.tests import SourceBaseTest
from tasks import update_collection_in_solr
from test_helper.base import create_user, create_source, create_organization, create_concept


def update_haystack_index():
    update_index.Command().handle()


class ConceptCreateViewTest(ConceptBaseTest):
    def setUp(self):
        super(ConceptCreateViewTest, self).setUp()

        display_name = LocalizedText(
            name='concept1',
            locale='en',
            type='FULLY_SPECIFIED'
        )

        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1, names=[display_name])

    def test_dispatch_with_head(self):
        update_haystack_index()
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic
        }

        response = self.client.get(reverse('concept-create', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))
        source_head_concepts = SourceVersion.objects.get(mnemonic='HEAD', versioned_object_id=self.source1.id).concepts
        self.assertEquals(1, len(source_head_concepts))
        self.assertEquals(content[0]['version'], source_head_concepts[0])

    def test_create_concept_without_fully_specified_name(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "ordinary"
            }, {
                "name": "gribal enfeksiyon",
                "locale": 'en',
                "name_type": "special"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concept_class_is_valid_attribute_negative(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "XYZQWERT",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(OPENMRS_CONCEPT_CLASS, response.content)

    def test_concept_class_is_valid_attribute_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_data_type_is_valid_attribute_negative(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "datatype": "XYZQWERT"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(OPENMRS_DATATYPE, response.content)

    def test_data_type_is_valid_attribute_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_name_type_is_valid_attribute_negative(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }, {
                "name": "test",
                "locale": 'en',
                "name_type": "QWERTY"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(OPENMRS_NAME_TYPE, response.content)

    def test_name_type_is_valid_attribute_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_description_type_is_valid_attribute_negative(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "XYZQWERT"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(OPENMRS_DESCRIPTION_TYPE, response.content)

    def test_desription_type_is_valid_attribute_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "FULLY_SPECIFIED"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_create_concept_with_more_than_one_preferred_name_in_concept(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "locale_preferred": "true",
                "name_type": "FULLY_SPECIFIED"
            }, {
                "name": "grip",
                "locale": 'en',
                "locale_preferred": "true",
                "name_type": "special"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_concept_with_more_than_one_preferred_name_in_source(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
        }

        data = json.dumps([{
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "locale_preferred": "false",
                "name_type": "FULLY_SPECIFIED"
            }, {
                "name": "gribal enfeksiyon",
                "locale": 'en',
                "locale_preferred": "true",
                "name_type": "special"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        }, {
            "id": "12399000",
            "concept_class": "Diagnosis",
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "names": [{
                "name": "grip",
                "locale": 'en',
                "locale_preferred": "false",
                "name_type": "FULLY_SPECIFIED"
            }, {
                "name": "gribal enfeksiyon",
                "locale": 'en',
                "locale_preferred": "true",
                "name_type": "special"
            }],
            "datatype": "None"}])

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_concept_without_fully_specified_name(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        responseCreate = self.client.post(reverse('concept-create', kwargs=kwargs), data,
                                          content_type='application/json')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
            'concept': '12399000'
        }

        data = json.dumps({
            "id": "12399000",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "grip",
                "locale": 'en',
                "name_type": "None"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        responseUpdate = self.client.put(reverse('concept-detail', kwargs=kwargs), data,
                                         content_type='application/json')

        self.assertEquals(responseUpdate.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_concept_without_changing_names(self):
        user = create_user()
        org = create_organization()
        source = create_source(user, organization=org)

        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': org.mnemonic,
            'source': source.mnemonic,
        }

        data = json.dumps({
            "id": "12399001",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "Grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        kwargs = {
            'org': org.mnemonic,
            'source': source.mnemonic,
            'concept': '12399001',
        }

        data = json.dumps({
            "id": "12399001",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "Grip",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "Gribal Enfeksiyon",
                "locale": 'en',
                "description_type": "None"
            }],
            "datatype": "None"
        })

        response = self.client.put(reverse('concept-detail', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_same_source_validation_rule_for_different_source_versions_on_concept_create(self):
        user = create_user()
        org = create_organization()
        source = create_source(user, organization=org)

        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': org.mnemonic,
            'source': source.mnemonic,
        }

        data = json.dumps({
            "id": "12399001",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "a",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        kwargs = {
            'org': org.mnemonic,
            'source': source.mnemonic,
            'concept': '12399001',
        }

        data = json.dumps({
            "id": "12399001",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "b",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        self.client.put(reverse('concept-detail', kwargs=kwargs), data, content_type='application/json')

        kwargs = {
            'org': org.mnemonic,
            'source': source.mnemonic,
        }

        data = json.dumps({
            "id": "12399002",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "a",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        response = self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_same_source_validation_rule_for_different_source_versions_on_concept_edit(self):
        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399001",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "a",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
        }

        data = json.dumps({
            "id": "12399002",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "b",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        self.client.post(reverse('concept-create', kwargs=kwargs), data, content_type='application/json')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source_for_openmrs.mnemonic,
            'concept': '12399002',
        }

        data = json.dumps({
            "id": "12399002",
            "concept_class": "Diagnosis",
            "names": [{
                "name": "a",
                "locale": 'en',
                "name_type": "FULLY_SPECIFIED",
                "locale_preferred": "True"
            }],
            "descriptions": [{
                "description": "description",
                "locale": "en",
                "description_type": "None"
            }],
            "datatype": "None"
        })

        response = self.client.put(reverse('concept-detail', kwargs=kwargs), data, content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dispatch_with_head_and_versions(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()

        (concept2, _) = create_concept(mnemonic='concept2', user=self.user1, source=self.source1)
        update_haystack_index()

        self.client.login(username='user1', password='user1')

        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('concept-create', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))
        source_head_concepts = SourceVersion.objects.get(mnemonic='HEAD', versioned_object_id=self.source1.id).concepts
        self.assertEquals(2, len(source_head_concepts))
        for concept in content:
            self.assertTrue(concept['version'] in source_head_concepts)

    def test_remove_names_on_edit_concept_should_fail(self):
        (concept, _) = create_concept(mnemonic='concept', user=self.user1, source=self.source1)
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org1.mnemonic,
            'source': self.source1.mnemonic,
            'concept': concept.mnemonic
        }

        data = json.dumps({
            "names": None
        })

        response = self.client.put(reverse('concept-detail', kwargs=kwargs), data,
                                   content_type='application/json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data['names'], [BASIC_NAMES_CANNOT_BE_EMPTY])


class ConceptVersionAllView(ConceptBaseTest):
    def test_collection_concept_version_list(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }

        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the second test collection'
        )
        Collection.persist_new(collection, self.user1, **kwargs)

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)
        source_version = SourceVersion.get_latest_version_of(source)
        expressions = []
        for i in range(11):
            mnemonic = 'concept' + str(i)
            create_concept(mnemonic=mnemonic, user=self.user1, source=source)

            reference = '/orgs/org1/sources/source/concepts/' + mnemonic + '/'
            expressions += [reference]
            concept = Concept.objects.get(mnemonic=mnemonic)
            concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id)
            source_version.update_concept_version(concept_version)

        collection.expressions = expressions
        collection.full_clean()
        collection.save()

        concept = Concept.objects.filter(mnemonic='concept1')[0]
        concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id)

        ConceptVersion.persist_clone(concept_version.clone(), self.user1)
        update_collection_in_solr(collection.get_head().id, collection.references)
        self.assertEquals(concept.num_versions, 2)

        self.client.login(username='user1', password='user1')
        url = reverse('concept-create', kwargs={'user': 'user1', 'collection': collection.mnemonic})
        response_for_page_1 = self.client.get(url)
        result = json.loads(response_for_page_1.content)
        self.assertEquals(response_for_page_1.status_code, 200)
        self.assertEquals(len(result), 10)
        self.assertEquals(response_for_page_1._headers.get('num_found')[1], '11')
        self.assertEquals(ConceptVersion.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count(), 12)
        versioned_object_ids = map(lambda v: v.get('id'), result)

        response_for_page_2 = self.client.get(url + '?page=2')
        self.assertEquals(response_for_page_2.status_code, 200)
        result = json.loads(response_for_page_2.content)
        self.assertEquals(len(result), 1)
        versioned_object_ids += (map(lambda v: v.get('id'), result))
        self.assertEquals(len(set(versioned_object_ids)), 11)


class OCLClient(Client):
    def put(self, path, data={}, content_type=MULTIPART_CONTENT,
            follow=False, **extra):
        """
        Requests a response from the server using POST.
        """
        response = self.my_put(path, data=data, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def my_put(self, path, data={}, content_type=MULTIPART_CONTENT, **extra):
        "Construct a PUT request."

        post_data = self._encode_data(data, content_type)

        parsed = urlparse(path)
        r = {
            'CONTENT_LENGTH': len(post_data),
            'CONTENT_TYPE': content_type,
            'PATH_INFO': self._get_path(parsed),
            'QUERY_STRING': force_str(parsed[4]),
            'REQUEST_METHOD': str('PUT'),
            'wsgi.input': FakePayload(post_data),
        }
        r.update(extra)
        return self.request(**r)


class MappingCreateViewTest(MappingBaseTest):
    def test_mappings_create_negative__no_params(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_from_concept(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As'
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_map_type(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'from_concept_url': self.concept1.url
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_to_concept(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])

    def test_mappings_create_positive__type2(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__both_types(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__self_mapping(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept1.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__not_authorized(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 404)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__other_user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user2.username,
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 404)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_positive__org_owner(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_positive__other_org_owner(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())


class MappingViewsTest(MappingBaseTest):
    client_class = OCLClient

    def setUp(self):
        super(MappingViewsTest, self).setUp()
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping1 = Mapping.objects.get(external_id='mapping1')

        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping2',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping2 = Mapping.objects.get(external_id='mapping2')

        # Create a new source
        self.source3 = Source(
            name='source3',
            mnemonic='source3',
            full_name='Source Three',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source3.com',
            description='This is the first third source',
        )
        kwargs = {
            'parent_resource': self.userprofile1
        }

        Source.persist_new(self.source3, self.user1, **kwargs)
        self.source3 = Source.objects.get(id=self.source3.id)
        self.source_version1 = SourceVersion.get_latest_version_of(self.source3)

        # Create a new version of the source
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
        }
        data = {
            'id': '2.0',
            'released': True
        }
        self.client.post(reverse('sourceversion-list', kwargs=kwargs), data)
        # Create a mapping in the latest version
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic
        }
        data = {
            'map_type': 'More specific than',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping4',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping4 = Mapping.objects.get(external_id='mapping4')
        self.source_version2 = SourceVersion.get_latest_version_of(self.source3)
        self.assertNotEquals(self.source_version1.id, self.source_version2.id)

        # Login as user2 who belongs to org2
        self.client.logout()
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping3',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping3 = Mapping.objects.get(external_id='mapping3')

        # Create a new source
        self.source4 = Source(
            name='source4',
            mnemonic='source4',
            full_name='Source Four',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source4.com',
            description='This is the fourth third source',
        )
        kwargs = {
            'parent_resource': self.org2
        }
        Source.persist_new(self.source4, self.user1, **kwargs)
        self.source4 = Source.objects.get(id=self.source4.id)
        self.source4_version1 = SourceVersion.get_latest_version_of(self.source4)

        # Create a mapping in the latest version
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic
        }
        data = {
            'map_type': 'Less specific than',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping5',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)

        # Create a new version of the source
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
        }
        data = {
            'id': '2.0',
            'released': True,
            'previous_version': 'HEAD'
        }
        self.client.post(reverse('sourceversion-list', kwargs=kwargs), data)

        self.mapping5 = Mapping.objects.get(external_id='mapping5')
        self.source4_version2 = SourceVersion.get_latest_version_of(self.source4)
        self.assertNotEquals(self.source4_version1.id, self.source4_version2.id)

        update_haystack_index()

    def test_mappings_list_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_mappings_list_positive__latest_version(self):
        mapping_version = MappingVersion.objects.get(versioned_object_id=self.mapping4.id)
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping_version.external_id, content['external_id'])
        self.assertEquals(mapping_version.map_type, content['map_type'])
        self.assertEquals(mapping_version.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping_version.to_source_url, content['to_source_url'])
        self.assertEquals(mapping_version.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping_version.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping_version.to_concept_url, content['to_concept_url'])
        self.assertEquals(self.mapping4.url, content['url'])  # in case of HEAD, main will be fetched

    @skip("need to adapt for mapping versions")
    def test_mappings_list_positive__explicit_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.userprofile1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_positive__contains_head_length(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

    def test_mappings_list_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    @skip("need to adapt for mapping versions")
    def test_mappings_list_positive__explicit_user_and_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_positive__contains_head_with_user(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

    def test_mappings_list_positive__org_owner(self):
        mapping_version = MappingVersion.objects.get(versioned_object_id=self.mapping3.id)
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping_version.external_id, content['external_id'])
        self.assertEquals(mapping_version.map_type, content['map_type'])
        self.assertEquals(mapping_version.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping_version.to_source_url, content['to_source_url'])
        self.assertEquals(mapping_version.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping_version.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping_version.to_concept_url, content['to_concept_url'])
        self.assertEquals(self.mapping3.url, content['url'])  # in case of HEAD, main will be fetched

    @skip("need to adapt for mapping versions")
    def test_mappings_list_positive__explicit_org_and_version(self):
        mapping = self.mapping5
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
            'version': self.source4_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_positive__contains_head(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
            'version': self.source4_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))
        self.assertEquals(1, int(content[0].get('version')))
        self.assertTrue(content[0].get('is_latest_version'))

    def test_mappings_get_positive(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1

        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_get_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1

        kwargs = {
            'user': self.user1,
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_get_positive__org_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping3
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_update_positive(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else',
            'update_comment': 'test update'
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])
        mapping_version = MappingVersion.objects.get(versioned_object_id=mapping.id, is_latest_version=True)
        self.assertEquals(mapping_version.update_comment, 'test update')

    def test_mappings_update_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else'
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

    def test_mappings_update_positive__org_owner(self):
        self.client.login(username='user2', password='user2')
        mapping = self.mapping3
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else'
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping3')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

    def test_mappings_update_negative__bad_url(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        from_concept = mapping.from_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'from_concept_url': 'http://does.not.exist/'
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        content = json.loads(response.content)
        self.assertTrue('from_concept_url' in content)

        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(from_concept, mapping.from_concept)

    def test_mappings_update_negative__self_reference(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        to_concept = mapping.to_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'to_concept_url': mapping.from_concept_url
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(to_concept, mapping.to_concept)

    def test_mappings_update_negative__mixed_types(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        to_concept = mapping.to_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'to_concept_code': '10101'
        }
        response = self.client.put(
            reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(to_concept, mapping.to_concept)

    @skip('this will be fixed when mapping version is integrated with search')
    def test_mappings_delete_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

        kwargs.update({'mapping': self.mapping1.mnemonic})
        response = self.client.delete(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

        mapping = Mapping.objects.get(id=self.mapping1.id)
        self.assertTrue(mapping.retired)

        del kwargs['mapping']
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

        response = self.client.get(
            "%s?includeRetired=true" % reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_mappings_delete_negative__not_found(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': '12345',
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    def test_mappings_delete_negative__not_allowed(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': self.mapping1.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    def test_concept_mappings_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic,
            'concept': self.concept1.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_concept_mappings_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic,
            'concept': self.concept1.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_concept_mappings_positive__org_owner(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept4.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '30303',
            'to_concept_name': 'quaternary',
            'external_id': 'mapping6',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)

        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'concept': self.concept4.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

    def test_concept_mappings_positive__include_inverse(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic,
            'concept': self.concept2.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

        response = self.client.get(
            "%s?includeInverseMappings=true" % reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

    def test_concept_mappings_positive__include_retired(self):
        self.client.login(username='user1', password='user1')
        Mapping.retire(self.mapping2, self.user1)
        kwargs = {
            'source': self.source1.mnemonic,
            'concept': self.concept1.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

        response = self.client.get(
            "%s?includeRetired=true" % reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_concept_mappings_negative__not_authorized(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'concept': self.concept4.mnemonic,
        }
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)

        self.source2.public_access = ACCESS_TYPE_NONE
        Source.persist_changes(self.source2, self.user2)
        response = self.client.get(reverse('concept-mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 403)

    @skip('Feature not ready.')
    def test_all_mappings__positive(self):
        self.source2.public_access = ACCESS_TYPE_EDIT
        Source.persist_changes(self.source2, self.user2)
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('all-mappings'))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(5, len(content))


class SourceViewTest(SourceBaseTest):
    def test_update_source_head(self):
        source = Source(
            name='source',
            mnemonic='source12',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source',
            is_active=True
        )

        kwargs = {
            'parent_resource': self.org1
        }

        Source.persist_new(source, self.user1, **kwargs)

        c = Client()
        c.login(username='user1', password='user1')
        response = c.put('/orgs/org1/sources/source12/', json.dumps({"website": "https://www.uno.com/",
                                                                     "description": "test desc",
                                                                     "default_locale": "ar",
                                                                     "source_type": "Indicator Registry",
                                                                     "full_name": "test_updated_name",
                                                                     "public_access": "View",
                                                                     "external_id": "57ac81eab29215063d7b1624",
                                                                     "supported_locales": "ar, en"}),
                         content_type="application/json")
        self.assertEquals(response.status_code, 200)

        head = source.get_head()
        self.assertEquals(head.mnemonic, 'HEAD')
        self.assertEquals(head.website, 'https://www.uno.com/')
        self.assertEquals(head.description, 'test desc')
        self.assertEquals(head.external_id, '57ac81eab29215063d7b1624')
        self.assertEquals(head.full_name, 'test_updated_name')


class CollectionViewTest(CollectionBaseTest):
    def test_update_source_head(self):
        collection = Collection(
            name='col1',
            mnemonic='col1',
            full_name='collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.col1.com',
            description='This is the first test source',
            is_active=True
        )

        kwargs = {
            'parent_resource': self.org1
        }

        Collection.persist_new(collection, self.user1, **kwargs)

        c = Client()
        c.login(username='user1', password='user1')
        response = c.put('/orgs/org1/collections/col1/', json.dumps({"website": "https://www.uno.com/",
                                                                     "description": "test desc",
                                                                     "default_locale": "ar",
                                                                     "collection_type": "Indicator Registry",
                                                                     "full_name": "test_updated_name",
                                                                     "public_access": "View",
                                                                     "external_id": "57ac81eab29215063d7b1624",
                                                                     "supported_locales": "ar, en"}),
                         content_type="application/json")
        self.assertEquals(response.status_code, 200)

        head = collection.get_head()
        self.assertEquals(head.mnemonic, 'HEAD')
        self.assertEquals(head.website, 'https://www.uno.com/')
        self.assertEquals(head.description, 'test desc')
        self.assertEquals(head.external_id, '57ac81eab29215063d7b1624')
        self.assertEquals(head.full_name, 'test_updated_name')


class SourceVersionViewTest(SourceBaseTest):
    def test_latest_version(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        for version in ['version1', 'version2']:
            source_version = SourceVersion(
                name=version,
                mnemonic=version,
                versioned_object=source,
                released=True,
                created_by=self.user1,
                updated_by=self.user1,
            )
            source_version.full_clean()
            source_version.save()

        self.client.login(username='user1', password='user1')

        response = self.client.get(
            reverse('sourceversion-latest-detail', kwargs={'org': self.org1.mnemonic, 'source': source.mnemonic}))
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEquals(result['id'], 'version2')
        self.assertEquals(result['released'], True)

    def test_new_version_with_duplicate_id_409_received(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()

        self.client.login(username='user1', password='user1')
        data = {
            'id': 'version1',
            'description': 'desc',
            'previous_version': 'HEAD'
        }
        response = self.client.post(
            reverse('sourceversion-list', kwargs={'org': self.org1.mnemonic, 'source': source.mnemonic}), data)
        self.assertEquals(response.status_code, 409)


class SourceVersionExportViewTest(SourceBaseTest):
    @mock_s3
    def test_source_version_concept_seeding(self):
        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        kwargs = {'parent_resource': source}
        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)
        (concept2, _) = create_concept(mnemonic='concept2', user=self.user1, source=source)

        mapping = Mapping(
            parent=source,
            map_type='SAME-AS',
            from_concept=concept1,
            to_source=source,
            to_concept=concept2,
            external_id='junk'
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)

        response = c.post('/orgs/' + self.org1.name + '/sources/' + source.mnemonic + '/versions/',
                          {'id': 'v1', 'description': 'v1'}
                          )
        source_version = SourceVersion.objects.get(mnemonic='v1')

        self.assertEquals(response.status_code, 201)
        self.assertEquals(source_version.active_concepts, 2)

    @mock_s3
    def test_post_invalid_version_404_received(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()
        kwargs = {'parent_resource': source}
        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'versionnotexist'
        }
        response = c.post(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    @mock_s3
    def test_get_invalid_version_404_received(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()
        kwargs = {'parent_resource': source}
        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)
        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'versionnotexist'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    @mock_s3
    def test_post(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()

        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)

        c = Client()
        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)
        # self.assertEquals(response['Last-Updated'], SourceVersion.get_latest_version_of(source).last_child_update.isoformat())
        # self.assertEquals(response['Last-Updated-Timezone'], 'America/New_York')

    @mock_s3
    def test_post_with_same_version_name_in_more_than_one_source(self):
        source1 = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        source2 = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source1, self.user1, **kwargs)
        Source.persist_new(source2, self.user1, **kwargs)

        source_version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version1.full_clean()
        source_version1.save()

        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source1)
        c = Client()

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

    @mock_s3
    def test_post_with_same_source_name_in_more_than_one_org(self):
        source1 = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        source2 = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs1 = {
            'parent_resource': self.org1
        }

        kwargs2 = {
            'parent_resource': self.org2
        }

        Source.persist_new(source1, self.user1, **kwargs1)
        Source.persist_new(source2, self.user1, **kwargs2)

        source_version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version1.full_clean()
        source_version1.save()
        create_concept(mnemonic='concept1', user=self.user1, source=source1)
        create_concept(mnemonic='concept1', user=self.user1, source=source2)
        c = Client()

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

    @mock_s3
    def test_post_with_head(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'HEAD'
        }
        response = c.post(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 405)

    @mock_s3
    def test_get_with_head(self):
        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        (concept1, _) = create_concept(mnemonic='concept1', user=self.user1, source=source)

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'HEAD'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 405)


class CollectionVersionExportViewTest(CollectionBaseTest):
    @mock_s3
    def test_get_invalid_version_404_received(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version.full_clean()
        collection_version.save()

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection.mnemonic,
            'version': 'versiondontexist'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    @mock_s3
    def test_post_invalid_version_404_received(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version.full_clean()
        collection_version.save()

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection.mnemonic,
            'version': 'versiondontexist'
        }
        response = c.post(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    @mock_s3
    def test_post_with_same_version_name_in_more_than_one_collection(self):
        collection1 = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        collection2 = Collection(
            name='collection2',
            mnemonic='collection2',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection1, self.user1, parent_resource=self.org1)

        Collection.persist_new(collection2, self.user1, parent_resource=self.org1)

        collection_version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version1.full_clean()
        collection_version1.save()

        collection_version2 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection2,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version2.full_clean()
        collection_version2.save()

        c = Client()
        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

    @mock_s3
    def test_post(self):
        collection1 = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection1, self.user1, parent_resource=self.org1)
        collection_version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version1.full_clean()
        collection_version1.save()

        c = Client()
        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

    @mock_s3
    def test_post_with_same_collection_name_in_more_than_one_org(self):
        collection1 = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        collection2 = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection1, self.user1, parent_resource=self.org1)

        Collection.persist_new(collection2, self.user1, parent_resource=self.org2)

        collection_version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version1.full_clean()
        collection_version1.save()

        c = Client()
        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

    @mock_s3
    def test_post_head(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection.mnemonic,
            'version': 'HEAD'
        }
        response = c.post(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 405)

    @mock_s3
    def test_get_head(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)

        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'collection': collection.mnemonic,
            'version': 'HEAD'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 405)


class CollectionReferenceViewTest(CollectionBaseTest):
    def test_destroy_reference(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }

        collection = Collection(
            name='collection2',
            mnemonic='collection2',
            full_name='Collection Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the second test collection'
        )
        Collection.persist_new(collection, self.user1, **kwargs)

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        (concept1, _) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=source,
        )

        reference = '/orgs/org1/sources/source/concepts/' + concept1.mnemonic + '/'
        collection.expressions = [reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(collection.references), 1)
        self.assertEquals(len(head.references), 1)
        self.assertEquals(len(head.concepts), 1)

        kwargs = {
            'user': 'user1',
            'collection': collection.mnemonic,
        }

        c = Client()
        data = json.dumps({'references': [concept1.get_latest_version.url],
                           'cascade': 'none'
                           })
        response = self.client.delete(reverse('collection-references', kwargs=kwargs), data,
                                      content_type='application/json')
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, {'message': 'ok!'})
        collection = Collection.objects.get(id=collection.id)
        head = CollectionVersion.get_head(collection.id)
        self.assertEquals(len(collection.references), 0)
        self.assertEquals(len(head.references), 0)
        self.assertEquals(len(head.concepts), 0)

    def test_reference_sorting(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }

        collection = Collection(
            name='collection2',
            mnemonic='collection2',
            full_name='Collection Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the second test collection'
        )
        Collection.persist_new(collection, self.user1, **kwargs)

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        (concept1, _) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=source,
        )

        (concept2, _) = create_concept(
            mnemonic='concept2',
            user=self.user1,
            source=source,
        )

        references = [
            '/orgs/org1/sources/source/concepts/' + concept1.mnemonic + '/',
            '/orgs/org1/sources/source/concepts/' + concept2.mnemonic + '/'
        ]
        collection.expressions = references
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(collection.references), 2)
        self.assertEquals(len(head.references), 2)
        self.assertEquals(len(head.concepts), 2)

        kwargs = {
            'user': 'user1',
            'collection': collection.mnemonic
        }

        c = Client()
        path = reverse('collection-references', kwargs=kwargs)

        # Default response
        response = c.get(path)
        response_content = json.loads(response.content)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(concept1.get_latest_version.url, response_content[0]['expression'])
        self.assertEquals(concept2.get_latest_version.url, response_content[1]['expression'])

        # Sort ASC
        response = c.get(path, {'search_sort': 'ASC'})
        response_content = json.loads(response.content)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(concept1.get_latest_version.url, response_content[0]['expression'])
        self.assertEquals(concept2.get_latest_version.url, response_content[1]['expression'])

        # Sort DESC
        response = c.get(path, {'search_sort': 'DESC'})
        response_content = json.loads(response.content)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(concept1.get_latest_version.url, response_content[1]['expression'])
        self.assertEquals(concept2.get_latest_version.url, response_content[0]['expression'])

    @skip('Skipping this as this task is now async and it is not handeled well in test')
    def test_add_all_concept_references(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }

        collection = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the one test collection'
        )
        Collection.persist_new(collection, self.user1, **kwargs)

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        for i in range(11):
            mnemonic = 'concept1' + str(i)

            create_concept(mnemonic=mnemonic, user=self.user1, source=source)

        c = Client()
        response = c.put(
            reverse('collection-references', kwargs={'user': 'user1', 'collection': collection.mnemonic}),
            json.dumps({
                'data': {
                    'concepts': '*',
                    'mappings': [],
                    'uri': '/orgs/org1/sources/source/HEAD/'
                }}),
            'application/json'
        )
        collection = Collection.objects.get(id=collection.id)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(collection.references), 11)

    @skip('Skipping this as this task is now async and it is not handeled well in test')
    def test_add_all_mappings_references(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }

        collection = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the one test collection'
        )
        Collection.persist_new(collection, self.user1, **kwargs)

        source = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(source, self.user1, **kwargs)

        (concept1, _) = create_concept(mnemonic='c1', user=self.user1, source=source)
        (concept2, _) = create_concept(mnemonic='c2', user=self.user1, source=source)
        (concept3, _) = create_concept(mnemonic='c3', user=self.user1, source=source)

        mapping1 = Mapping(
            parent=source,
            map_type='SAME-AS',
            from_concept=concept1,
            to_concept=concept2,
            external_id='something'
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping1, self.user1, **kwargs)

        mapping2 = Mapping(
            parent=source,
            map_type='SAME-AS',
            from_concept=concept2,
            to_concept=concept3,
            external_id='anything'
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping2, self.user1, **kwargs)

        c = Client()
        response = c.put(
            reverse('collection-references', kwargs={'user': 'user1', 'collection': collection.mnemonic}),
            json.dumps({
                'data': {
                    'concepts': [concept1.uri],
                    'mappings': '*',
                    'uri': '/orgs/org1/sources/source/HEAD/'
                }}),
            'application/json'
        )
        collection = Collection.objects.get(id=collection.id)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(collection.references), 3)


class CollectionVersionViewTest(SourceBaseTest):
    def test_latest_version(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)

        for version in ['version1', 'version2']:
            collection_version = CollectionVersion(
                name=version,
                mnemonic=version,
                versioned_object=collection,
                released=True,
                created_by=self.user1,
                updated_by=self.user1,
            )
            collection_version.full_clean()
            collection_version.save()

        self.client.login(username='user1', password='user1')

        response = self.client.get(reverse('collectionversion-latest-detail',
                                           kwargs={'org': self.org1.mnemonic, 'collection': collection.mnemonic}))
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEquals(result['id'], 'version2')
        self.assertEquals(result['released'], True)

    def test_new_version_with_duplicate_id_409_received(self):
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(collection, self.user1, parent_resource=self.org1)

        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        collection_version.full_clean()
        collection_version.save()

        self.client.login(username='user1', password='user1')
        data = {
            'id': 'version1',
            'description': 'desc',
            'previous_version': 'HEAD'
        }
        response = self.client.post(reverse('collectionversion-list',
                                            kwargs={'org': self.org1.mnemonic, 'collection': collection.mnemonic}),
                                    data)
        self.assertEquals(response.status_code, 409)


class SourceDeleteViewTest(SourceBaseTest):
    def setUp(self):
        self.tearDown()
        super(SourceDeleteViewTest, self).setUp()
        self.source1 = Source(
            name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source',
        )
        kwargs = {
            'parent_resource': self.org1,
        }
        Source.persist_new(self.source1, self.org1, **kwargs)

        (self.concept1, _) = create_concept(mnemonic='1', user=self.org1, source=self.source1)
        (self.concept2, _) = create_concept(mnemonic='2', user=self.org1, source=self.source1)

        self.mapping = Mapping(
            parent=self.source1,
            map_type='SAME-AS',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='junk'
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(self.mapping, self.org1, **kwargs)

        self.collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        Collection.persist_new(self.collection, self.org1, parent_resource=self.org1)

        self.collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection,
            released=True,
            created_by=self.org1,
            updated_by=self.org1,
        )
        CollectionVersion.persist_new(self.collection_version)

    def test_delete_source_with_referenced_mapping_in_collection(self):
        self.collection.expressions = [self.mapping.uri]
        self.collection.full_clean()
        self.collection.save()

        self.client.login(username='user1', password='user1')
        path = reverse('source-detail', kwargs={'org': self.org1.name, 'source': self.source1.mnemonic})
        response = self.client.delete(path)
        self.assertEquals(response.status_code, 400)
        message = json.loads(response.content)['detail']
        self.assertTrue(
            'This source cannot be deleted because others have created mapping or references that point to it.' in message)

    def test_delete_source_with_referenced_concept_in_collection(self):
        self.collection.expressions = [self.concept1.uri]
        self.collection.full_clean()
        self.collection.save()

        self.client.login(username='user1', password='user1')
        path = reverse('source-detail', kwargs={'org': self.org1.name, 'source': self.source1.mnemonic})
        response = self.client.delete(path)
        self.assertEquals(response.status_code, 400)
        message = json.loads(response.content)['detail']
        self.assertTrue(
            'This source cannot be deleted because others have created mapping or references that point to it.' in message)

    def test_delete_source_with_concept_referenced_in_mapping_of_another_source(self):
        self.source2 = Source(
            name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source',
        )
        kwargs = {
            'parent_resource': self.org1,
        }
        Source.persist_new(self.source2, self.org1, **kwargs)

        (self.concept3, _) = create_concept(mnemonic='3', user=self.org1, source=self.source2)

        self.mapping2 = Mapping(
            parent=self.source2,
            map_type='SAME-AS',
            from_concept=self.concept1,
            to_concept=self.concept3,
            external_id='junk'
        )
        kwargs = {
            'parent_resource': self.source2,
        }
        Mapping.persist_new(self.mapping2, self.org1, **kwargs)

        self.client.login(username='user1', password='user1')
        path = reverse('source-detail', kwargs={'org': self.org1.name, 'source': self.source1.mnemonic})
        response = self.client.delete(path)
        self.assertEquals(response.status_code, 400)
        message = json.loads(response.content)['detail']
        self.assertTrue('To delete this source, you must first delete all linked mappings and references and try again.' in message)
