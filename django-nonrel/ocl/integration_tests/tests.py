from django.contrib.auth.models import User

from concepts.models import Concept, LocalizedText, ConceptVersion
from concepts.importer import ConceptsImporter
from mappings.importer import MappingsImporter
from mappings.models import Mapping
from sources.models import Source, SourceVersion
from concepts.tests import ConceptBaseTest
from mappings.tests import MappingBaseTest

from django.core.urlresolvers import reverse
from integration_tests.models import TestStream
import json
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
