import json
from moto import mock_s3
from urlparse import urlparse
from concepts.importer import ConceptsImporter
from concepts.models import Concept, LocalizedText, ConceptVersion
from concepts.tests import ConceptBaseTest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django.test.client import MULTIPART_CONTENT, FakePayload
from django.utils.unittest.case import skip
from integration_tests.models import TestStream
from mappings.importer import MappingsImporter
from mappings.models import Mapping
from mappings.tests import MappingBaseTest
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_NONE
from sources.models import Source, SourceVersion
from collection.models import Collection, CollectionVersion
from sources.tests import SourceBaseTest
from collection.tests import CollectionBaseTest
from django.utils.encoding import force_str

# @override_settings(HAYSTACK_SIGNAL_PROCESSOR='haystack.signals.BaseSignalProcessor') #see if this can also be done at some point later
class ConceptImporterTest(ConceptBaseTest):
    def setUp(self):
        super(ConceptImporterTest, self).setUp()
        User.objects.create(
            username='superuser',
            password='superuser',
            email='superuser@test.com',
            last_name='Super',
            first_name='User',
            is_superuser=True
        )
        self.testfile = open('./integration_tests/one_concept.json', 'rb')

    def test_import_job_for_one_record(self):
        stdout_stub = TestStream()
        importer = ConceptsImporter(self.source1, self.testfile, 'test', stdout_stub, TestStream())
        importer.import_concepts(total=1)
        self.assertTrue('Created new concept: 1 = Diagnosis' in stdout_stub.getvalue())
        self.assertTrue('Finished importing concepts!' in stdout_stub.getvalue())
        inserted_concept = Concept.objects.get(mnemonic='1')
        self.assertEquals(inserted_concept.parent, self.source1)
        inserted_concept_version = ConceptVersion.objects.get(versioned_object_id=inserted_concept.id)
        source_version_latest = SourceVersion.get_latest_version_of(self.source1)

        self.assertEquals(source_version_latest.concepts, [inserted_concept_version.id])
    
    def test_import_job_for_change_in_data(self):
        stdout_stub = TestStream()
        source_version_latest = SourceVersion.get_latest_version_of(self.source1)
        concept = Concept(
            mnemonic='1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Diagnosis',
            external_id='1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
            names=[self.name])
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(concept, self.user1, **kwargs)
        
        importer = ConceptsImporter(self.source1, self.testfile, 'test', stdout_stub, TestStream())
        importer.import_concepts(total=1)
        all_concept_versions = ConceptVersion.objects.all()
        self.assertEquals(len(all_concept_versions), 2)
        
        concept = Concept.objects.get(mnemonic='1')
        latest_concept_version = [version for version in all_concept_versions if version.previous_version][0]
        
        self.assertEquals(len(latest_concept_version.names), 4)
        self.assertTrue(('Updated concept, replacing version ID ' + latest_concept_version.previous_version.id) in stdout_stub.getvalue())
        self.assertTrue('concepts of 1 1 - 1 updated' in stdout_stub.getvalue())

class MappingImporterTest(MappingBaseTest):
    def setUp(self):
        super(MappingImporterTest, self).setUp()
        User.objects.create(
            username='superuser',
            password='superuser',
            email='superuser@test.com',
            last_name='Super',
            first_name='User',
            is_superuser=True
        )
        self.testfile = open('./integration_tests/one_mapping.json', 'rb')

    def test_import_job_for_one_record(self):
        stdout_stub = TestStream()
        stderr_stub = TestStream()
        importer = MappingsImporter(self.source1, self.testfile, stdout_stub, stderr_stub, 'test')
        importer.import_mappings(total=1)
        self.assertTrue('Created new mapping:' in stdout_stub.getvalue())
        self.assertTrue('/users/user1/sources/source1/:413532003' in stdout_stub.getvalue())
        inserted_mapping = Mapping.objects.get(to_concept_code='413532003')
        self.assertEquals(inserted_mapping.to_source, self.source1)
        self.assertEquals(inserted_mapping.from_source, self.source2)
        mapping_ids = SourceVersion.get_latest_version_of(self.source1).mappings
        self.assertEquals(mapping_ids[0], inserted_mapping.id)

    def test_import_job_for_change_in_data(self):
        stdout_stub = TestStream()
        stderr_stub = TestStream()
        mapping = Mapping.objects.create(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='SAME-AS',
            from_concept=self.concept3,
            to_source=self.source1,
            to_concept_code='413532003',
            external_id='junk'
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        source_version.mappings = [mapping.id]
        source_version.save()

        importer = MappingsImporter(self.source1, self.testfile, stdout_stub, stderr_stub, 'test')
        importer.import_mappings(total=1)
        self.assertTrue('mappings of 1 1 - 1 updated' in stdout_stub.getvalue())
        self.assertTrue(('Updated mapping with ID ' + mapping.id) in stdout_stub.getvalue())
        updated_mapping = Mapping.objects.get(to_concept_code='413532003')
        self.assertTrue(updated_mapping.retired)
        self.assertEquals(updated_mapping.external_id, '70279ABBBBBBBBBBBBBBBBBBBBBBBBBBBBBB')

class ConceptCreateViewTest(ConceptBaseTest):
    def setUp(self):
        super(ConceptCreateViewTest, self).setUp()
        self.concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            external_id='EXTID',
            names=[self.name],
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en'
        )
        self.concept1.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, self.user1, **kwargs)


    def test_dispatch_with_head(self):
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

        concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='not First',
            external_id='EXTID',
            names=[self.name],
        )
        display_name = LocalizedText(
            name='concept2',
            locale='en'
        )
        concept2.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(concept2, self.user1, **kwargs)


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
            'CONTENT_TYPE':   content_type,
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   force_str(parsed[4]),
            'REQUEST_METHOD': str('PUT'),
            'wsgi.input':     FakePayload(post_data),
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

        # Create a new version of the source
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
        }
        data = {
            'id': '2.0',
            'released': True
        }
        self.client.post(reverse('sourceversion-list', kwargs=kwargs), data)
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
        self.mapping5 = Mapping.objects.get(external_id='mapping5')
        self.source4_version2 = SourceVersion.get_latest_version_of(self.source4)
        self.assertNotEquals(self.source4_version1.id, self.source4_version2.id)

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
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic
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

    def test_mappings_list_positive__explicit_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
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

    def test_mappings_list_negative__explicit_version(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

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

    def test_mappings_list_negative__explicit_user_and_version(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

    def test_mappings_list_positive__org_owner(self):
        mapping = self.mapping3
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
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

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

    def test_mappings_list_negative__explicit_org_and_version(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
            'version': self.source4_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

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
        self.assertEquals(response.status_code, 404)

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
            mnemonic='source11',
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

        data = {
            'full_name': "s11"
        }

        kwargs = {
            'source': source.mnemonic,
            'user': self.user1.username

        }

        # c = Client()
        # self.client.post('/login/', {'username': 'user1', 'password': 'user1'})
        self.client.login(username='user1', password='user1')
        # response = self.client.put('/users/user1/sources/source11/', data=data)
        response = self.client.put(reverse('source-detail', kwargs=kwargs), data=data)
        print 'res===', response.status_code
        head=source.get_head()
        self.assertEquals(head.mnemonic,'HEAD')
        self.assertEquals(head.full_name,'Source One')


class SourceVersionExportViewTest(SourceBaseTest):
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
        kwargs = {'parent_resource': source}
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=source, concept_class='First', names=[self.name])
        Concept.persist_new(concept1, self.user1, **kwargs)
        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['lastUpdated'], SourceVersion.get_latest_version_of(source).last_child_update.isoformat())
        self.assertEquals(response['lastUpdatedTimezone'], 'America/New_York')

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
        kwargs = {'parent_resource': source1}
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=source1, concept_class='First', names=[self.name])
        Concept.persist_new(concept1, self.user1, **kwargs)
        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)

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
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=source1, concept_class='First', names=[self.name])
        Concept.persist_new(concept1, self.user1, **{'parent_resource': source1})
        Concept.persist_new(concept1, self.user1, **{'parent_resource': source2})
        c = Client()
        c.post('/login/', {'username': 'user1', 'password': 'user1'})

        kwargs = {
            'org': self.org1.mnemonic,
            'source': source1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('sourceversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)


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

        kwargs = {'parent_resource': source}
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=source, concept_class='First',
                           names=[self.name])
        Concept.persist_new(concept1, self.user1, **kwargs)
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

        kwargs = {'parent_resource': source}
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=source, concept_class='First',
                           names=[self.name])
        Concept.persist_new(concept1, self.user1, **kwargs)
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
    def test_post(self):
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
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['lastUpdated'], CollectionVersion.get_latest_version_of(collection).last_child_update.isoformat())
        self.assertEquals(response['lastUpdatedTimezone'], 'America/New_York')

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

        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection1,
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
            'collection': collection1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)

    @mock_s3
    def test_post_with_same_source_name_in_more_than_one_org(self):
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

        Collection.persist_new(collection2, self.user1, parent_resource=self.org2)

        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection1,
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
            'collection': collection1.mnemonic,
            'version': 'version1'
        }
        response = c.get(reverse('collectionversion-export', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)


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

        concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)


        reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.filter()[0].mnemonic + '/'
        collection.expression = reference
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(collection.references), 1)
        self.assertEquals(len(head.references), 1)
        self.assertEquals(len(head.concepts), 1)

        kwargs = {
            'user': 'user1',
            'collection': collection.mnemonic
        }

        c = Client()
        path = reverse('collection-references', kwargs=kwargs)
        data = json.dumps({'references': [reference]})
        response = c.delete(path, data, 'application/json')
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, {'references': []})
        collection = Collection.objects.get(id=collection.id)
        head = CollectionVersion.get_head(collection.id)
        self.assertEquals(len(collection.references), 0)
        self.assertEquals(len(head.references), 0)
        self.assertEquals(len(head.concepts), 0)

    def test_retrieve(self):
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

        expected_references = []
        for i in range(11):
            mnemonic = 'concept1' + str(i)
            concept1 = Concept(
                mnemonic=mnemonic,
                created_by=self.user1,
                updated_by=self.user1,
                parent=source,
                concept_class='First',
                names=[LocalizedText.objects.create(name='User', locale='es')],
            )
            kwargs = {
                'parent_resource': source,
            }
            Concept.persist_new(concept1, self.user1, **kwargs)
            reference = '/orgs/org1/sources/source/concepts/' + mnemonic + '/'
            expected_references += [{'reference_type': 'concepts', 'expression': reference}]
            collection.expression = reference
            collection.full_clean()
            collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(collection.references), 11)
        self.assertEquals(len(head.references), 11)
        self.assertEquals(len(head.concepts), 11)

        c = Client()
        path = reverse('collection-references', kwargs={'user': 'user1', 'collection': collection.mnemonic})
        response = c.get(path)
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, expected_references[:10])

        response = c.get(path + '?page=1')
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, expected_references[:10])

        response = c.get(path + '?page=2')
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [expected_references[10]])