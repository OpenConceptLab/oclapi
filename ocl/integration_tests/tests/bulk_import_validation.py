from django.contrib.auth.models import User

from concepts.importer import ConceptsImporter, ValidationLogger
from concepts.validation_messages import OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE, OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, \
    OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED, OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE, \
    OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME, OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE
from concepts.models import Concept, ConceptVersion
from concepts.tests import ConceptBaseTest
from integration_tests.models import TestStream
from mappings.importer import MappingsImporter
from mappings.models import Mapping
from mappings.models import MappingVersion
from mappings.tests import MappingBaseTest
from sources.models import SourceVersion
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS, LOOKUP_CONCEPT_CLASSES
from test_helper.base import create_source, create_user, create_concept


class BulkConceptImporterTest(ConceptBaseTest):
    def setUp(self):
        super(BulkConceptImporterTest, self).setUp()
        User.objects.create(
            username='superuser',
            password='superuser',
            email='superuser@test.com',
            last_name='Super',
            first_name='User',
            is_superuser=True
        )

    def test_import_single_concept_without_fully_specified_name(self):
        self.testfile = open('./integration_tests/fixtures/concept_without_fully_specified_name.json', 'rb')
        stderr_stub = TestStream()
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        importer = ConceptsImporter(source, self.testfile, 'test', TestStream(), stderr_stub, save_validation_errors=False)
        importer.import_concepts(total=1)
        self.assertTrue(OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME in stderr_stub.getvalue())

    def test_import_concepts_with_invalid_records(self):
        self.testfile = open('./integration_tests/fixtures/valid_invalid_concepts.json', 'rb')
        stderr_stub = TestStream()
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        importer = ConceptsImporter(source, self.testfile, 'test', TestStream(), stderr_stub, save_validation_errors=False)
        importer.import_concepts(total=7)
        self.assertTrue(OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME in stderr_stub.getvalue())
        self.assertTrue(OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE in stderr_stub.getvalue())
        self.assertEquals(5, Concept.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())
        self.assertEquals(5, ConceptVersion.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())

    def test_update_concept_with_invalid_record(self):
        (concept, _) = create_concept(mnemonic='1', user=self.user1, source=self.source1, names=[self.name])

        self.testfile = open('./integration_tests/fixtures/concept_without_fully_specified_name.json', 'rb')
        stderr_stub = TestStream()
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        importer = ConceptsImporter(source, self.testfile, 'test', TestStream(), stderr_stub, save_validation_errors=False)
        importer.import_concepts(total=1)
        self.assertTrue(OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME in stderr_stub.getvalue())
        self.assertEquals(1, Concept.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())
        self.assertEquals(1, ConceptVersion.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())

    def test_import_concepts_into_openmrs_validated_source_with_valid_records(self):
        test_file = open('./integration_tests/fixtures/concepts_for_openmrs_validation.json', 'rb')
        stderr_stub = TestStream()
        user = create_user()
        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        importer = ConceptsImporter(source, test_file, 'test', TestStream(), stderr_stub, save_validation_errors=False)
        importer.import_concepts(total=5)

        self.assertTrue(OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME in stderr_stub.getvalue())
        self.assertTrue(OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED in stderr_stub.getvalue())
        self.assertTrue(OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED in stderr_stub.getvalue())
        self.assertTrue(OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE in stderr_stub.getvalue())

        self.assertEquals(2, Concept.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())
        self.assertEquals(2, ConceptVersion.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES).count())

    def test_validation_error_file_output(self):
        self.testfile = open('./integration_tests/fixtures/valid_invalid_concepts.json', 'rb')
        stderr_stub = TestStream()

        logger = ValidationLogger(output=TestStream())
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        importer = ConceptsImporter(source, self.testfile, 'test', TestStream(), stderr_stub, validation_logger=logger)
        importer.import_concepts(total=7)

        self.assertTrue('MNEMONIC;ERROR;JSON' in logger.output.getvalue())
        self.assertTrue('4;%s' % OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME  in logger.output.getvalue())
        self.assertTrue('7;%s' % OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE  in logger.output.getvalue())

    def test_validation_error_file_exists(self):
        self.testfile = open('./integration_tests/fixtures/valid_invalid_concepts.json', 'rb')
        stderr_stub = TestStream()

        output_file_name = 'test_file.csv'
        logger = ValidationLogger(output_file_name=output_file_name)

        importer = ConceptsImporter(create_source(user=self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS), self.testfile, 'test', TestStream(), stderr_stub,
                                    validation_logger=logger)
        importer.import_concepts(total=7)
        from os import path, remove
        self.assertTrue(path.exists(output_file_name))
        remove(output_file_name)


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
        self.testfile = open('./integration_tests/fixtures/one_concept.json', 'rb')

    def test_import_job_for_one_record(self):
        stdout_stub = TestStream()
        importer = ConceptsImporter(self.source1, self.testfile, 'test', stdout_stub, TestStream(), save_validation_errors=False)
        importer.import_concepts(total=1)
        self.assertTrue('Created new concept: 1 = Diagnosis' in stdout_stub.getvalue())
        self.assertTrue('Finished importing concepts!' in stdout_stub.getvalue())
        inserted_concept = Concept.objects.get(mnemonic='1')
        self.assertEquals(inserted_concept.parent, self.source1)
        inserted_concept_version = ConceptVersion.objects.get(versioned_object_id=inserted_concept.id)
        source_version_latest = SourceVersion.get_latest_version_of(self.source1)

        self.assertEquals(source_version_latest.get_concept_ids(), [inserted_concept_version.id])

    def test_import_job_for_change_in_data(self):
        stdout_stub = TestStream()
        create_concept(mnemonic='1', user=self.user1, source=self.source1)

        importer = ConceptsImporter(self.source1, self.testfile, 'test', stdout_stub, TestStream(), save_validation_errors=False)
        importer.import_concepts(total=1)
        all_concept_versions = ConceptVersion.objects.exclude(concept_class__in=LOOKUP_CONCEPT_CLASSES)
        self.assertEquals(len(all_concept_versions), 2)

        latest_concept_version = [version for version in all_concept_versions if version.previous_version][0]

        self.assertEquals(len(latest_concept_version.names), 4)

        self.assertTrue(('Updated concept, replacing version ID ' + latest_concept_version.previous_version.id) in stdout_stub.getvalue())
        self.assertTrue('**** Processed 1 out of 1 concepts - 1 updated, ****' in stdout_stub.getvalue())


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
        self.testfile = open('./integration_tests/fixtures/one_mapping.json', 'rb')

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
        mapping_ids = SourceVersion.get_latest_version_of(self.source1).get_mapping_ids()
        mapping_version = MappingVersion.objects.get(versioned_object_id=inserted_mapping.id, is_latest_version=True)
        self.assertEquals(mapping_ids[0], mapping_version.id)

    def test_import_job_for_one_invalid_record(self):
        stdout_stub = TestStream()
        stderr_stub = TestStream()
        invalid_json_file = open('./integration_tests/fixtures/one_invalid_mapping.json', 'rb')
        importer = MappingsImporter(self.source1, invalid_json_file, stdout_stub, stderr_stub, 'test')
        importer.import_mappings(total=1)
        self.assertTrue('Cannot map concept to itself.' in stderr_stub.getvalue())

    def test_import_job_for_change_in_data(self):
        stdout_stub = TestStream()
        stderr_stub = TestStream()
        mapping = Mapping(
            parent=self.source1,
            map_type='SAME-AS',
            from_concept=self.concept3,
            to_source=self.source1,
            to_concept_code='413532003',
            external_id='junk'
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        source_version = SourceVersion.get_latest_version_of(self.source1)
        source_version.mappings = [mapping.id]
        source_version.save()

        importer = MappingsImporter(self.source1, self.testfile, stdout_stub, stderr_stub, 'test')
        importer.import_mappings(total=1)

        self.assertTrue('**** Processed 1 out of 1 mappings - 1 updated, ****' in stdout_stub.getvalue())
        self.assertTrue(('Updated mapping with ID ' + mapping.id) in stdout_stub.getvalue())
        updated_mapping = Mapping.objects.get(to_concept_code='413532003')
        self.assertTrue(updated_mapping.retired)
        self.assertEquals(updated_mapping.external_id, '70279ABBBBBBBBBBBBBBBBBBBBBBBBBBBBBB')

    def test_update_mapping_with_invalid_record(self):
        mapping = Mapping(
            parent=self.source1,
            map_type='SAME-AS',
            from_concept=self.concept3,
            to_concept=self.concept1
        )
        kwargs = {
            'parent_resource': self.source1,
        }

        Mapping.persist_new(mapping, self.user1, **kwargs)
        source_version = SourceVersion.get_latest_version_of(self.source1)
        source_version.mappings = [mapping.id]
        source_version.save()
        stderr_stub = TestStream()
        invalid_json_file = open('./integration_tests/fixtures/one_internal_invalid_mapping.json', 'rb')
        importer = MappingsImporter(self.source1, invalid_json_file, TestStream(), stderr_stub, 'test')
        importer.import_mappings(total=1)
        self.assertTrue(
            "Must specify either 'to_concept' or 'to_source' & 'to_concept_code'. Cannot specify both." in stderr_stub.getvalue())

    def test_import_valid_invalid_mappings(self):
        stdout_stub = TestStream()
        stderr_stub = TestStream()
        invalid_json_file = open('./integration_tests/fixtures/valid_invalid_mapping.json', 'rb')
        importer = MappingsImporter(self.source1, invalid_json_file, stdout_stub, stderr_stub, 'test')
        importer.import_mappings(total=5)
        self.assertTrue('Cannot map concept to itself.' in stderr_stub.getvalue())
        self.assertTrue("Must specify either 'to_concept' or 'to_source' & " in stderr_stub.getvalue())
        self.assertEquals(3, Mapping.objects.count())
        self.assertEquals(3, MappingVersion.objects.count())