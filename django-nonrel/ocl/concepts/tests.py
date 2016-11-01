"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from concepts.views import ConceptVersionListView
from oclapi.models import ACCESS_TYPE_VIEW
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import *


class ConceptBaseTest(OclApiBaseTestCase):

    def setUp(self):
        self.user1 = User.objects.create(
            username='user1',
            password='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User'
        )
        self.user2 = User.objects.create(
            username='user2',
            email='user2@test.com',
            last_name='Two',
            first_name='User'
        )

        self.userprofile1 = UserProfile.objects.create(user=self.user1, mnemonic='user1')
        self.userprofile2 = UserProfile.objects.create(user=self.user2, mnemonic='user2')

        self.org1 = Organization.objects.create(name='org1', mnemonic='org1')
        self.org2 = Organization.objects.create(name='org2', mnemonic='org2')

        self.source1 = Source(
            name='source1',
            mnemonic='source1',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source',
            custom_validation_schema=None
        )

        kwargs = {
            'parent_resource': self.org1
        }
        Source.persist_new(self.source1, self.user1, **kwargs)
        self.source1 = Source.objects.get(id=self.source1.id)

        self.source2 = Source(
            name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type='Reference',
            public_access=ACCESS_TYPE_VIEW,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.source2.com',
            description='This is the second test source',
            custom_validation_schema=None
        )
        kwargs = {
            'parent_resource': self.org2,
        }
        Source.persist_new(self.source2, self.user2, **kwargs)
        self.source2 = Source.objects.get(id=self.source2.id)

        self.name = LocalizedText.objects.create(name='Fred', locale='es', type='FULLY_SPECIFIED')
        self.description = LocalizedText.objects.create(name='guapo', locale='es')

class ConceptTest(ConceptBaseTest):

    def test_create_concept_positive(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_create_concept_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                concept_class='First',
                names=[self.name],
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                parent=self.source1,
                updated_by=self.user1,
                concept_class='First',
                names=[self.name],
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_class(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                names=[self.name],
            )
            concept.full_clean()
            concept.save()

    def test_concept_display_name(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en',
            locale_preferred=True,
            type='FULLY_SPECIFIED'
        )
        concept.names.append(display_name)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name.name, concept.display_name)
        self.assertEquals(display_name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_concept_display_name_preferred(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        display_name1 = LocalizedText(
            name='concept1',
            locale='en',
            locale_preferred=True,
            type = 'FULLY_SPECIFIED'
        )
        concept.names.append(display_name1)
        display_name2 = LocalizedText(
            name='le concept1',
            locale='fr',
            type = 'FULLY_SPECIFIED'
        )
        concept.names.append(display_name2)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name1.name, concept.display_name)
        self.assertEquals(display_name1.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_concept_access_changes_with_source(self):
        public_access = self.source1.public_access
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            public_access=public_access,
            concept_class='First',
            names=[self.name],
        )
        concept.full_clean()
        concept.save()

        self.assertEquals(self.source1.public_access, concept.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

        concept = Concept.objects.get(id=concept.id)
        self.assertNotEquals(public_access, self.source1.public_access)
        self.assertEquals(self.source1.public_access, concept.public_access)

    def test_get_latest_version(self):
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
            mnemonic='concept12',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type = 'FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)
        concept = Concept.objects.get(mnemonic=concept1.mnemonic)
        concept_version1 = ConceptVersion.objects.get(versioned_object_id=concept.id)
        self.assertEquals(concept.get_latest_version.id, concept_version1.id)

class ConceptBasicValidationTest(ConceptBaseTest):
    def test_unique_preferred_name_per_source_positive(self):
        concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText(name='Concept Unique Preferred Name 1', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText(name='Concept Unique Preferred Name 2', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors1 = Concept.persist_new(concept1, self.user1, **kwargs)
        errors2 = Concept.persist_new(concept2, self.user1, **kwargs)

        self.assertEquals(0, len(errors1))
        self.assertEquals(0, len(errors2))

    def test_duplicate_preferred_name_per_source_should_fail(self):
        concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors1 = Concept.persist_new(concept1, self.user1, **kwargs)
        errors2 = Concept.persist_new(concept2, self.user1, **kwargs)

        self.assertEquals(0, len(errors1))
        self.assertEquals(1, len(errors2))
        self.assertEquals(errors2['names'][0], 'Concept preferred name should be unique for same source and locale')

    def test_duplicate_preferred_name_per_source_should_pass_if_not_preferred(self):
        concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='en', locale_preferred=False, type='FULLY_SPECIFIED')
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors1 = Concept.persist_new(concept1, self.user1, **kwargs)
        errors2 = Concept.persist_new(concept2, self.user1, **kwargs)

        self.assertEquals(0, len(errors1))
        self.assertEquals(0, len(errors2))

    def test_unique_preferred_name_per_locale_within_concept_negative(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED'),
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED'),
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors = Concept.persist_new(concept, self.user1, **kwargs)

        self.assertEquals(1, len(errors))

    def test_unique_preferred_name_per_locale_within_concept_positive(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='en', locale_preferred=True, type='FULLY_SPECIFIED'),
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED'),
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors = Concept.persist_new(concept, self.user1, **kwargs)

        self.assertEquals(0, len(errors))

    def test_unique_preferred_name_per_locale_within_source_negative(self):
        concept1 = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Concept Non Unique Preferred Name', locale='es', locale_preferred=True, type='FULLY_SPECIFIED')
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors1 = Concept.persist_new(concept1, self.user1, **kwargs)
        errors2 = Concept.persist_new(concept2, self.user1, **kwargs)

        self.assertEquals(0, len(errors1))
        self.assertEquals(1, len(errors2))
        self.assertEquals(errors2['names'][0], 'Concept preferred name should be unique for same source and locale')

    def test_at_least_one_fully_specified_name_per_concept_negative(self):
        concept = Concept(
            mnemonic='concept',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[
                LocalizedText.objects.create(name='Fully Specified Name 1', type='SYNONYM'),
                LocalizedText.objects.create(name='Fully Specified Name 2', type='SYNONYM')
            ]
        )

        kwargs = {
            'parent_resource': self.source1,
        }

        errors = Concept.persist_new(concept, self.user1, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0], 'Concept requires at least one fully specified name')

class ConceptClassMethodsTest(ConceptBaseTest):

    def test_persist_new_positive(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)
        self.assertEquals(concept_version.mnemonic, concept_version.id)

    def test_persist_new_negative__no_owner(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, None, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('created_by' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.concepts))

    def test_persist_new_negative__no_parent(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        errors = Concept.persist_new(concept, self.user1)
        self.assertEquals(1, len(errors))
        self.assertTrue('parent' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.concepts))

    def test_persist_new_negative__repeated_mnemonic(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

        # Repeat with same mnemonic
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))

    def test_persist_new_positive__repeated_mnemonic(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

        # Repeat with same mnemonic, different parent
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source2,
            concept_class='First',
            names=[self.name],
        )
        source_version = SourceVersion.get_latest_version_of(self.source2)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source2,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source2.parent_resource, concept.owner_name)
        self.assertEquals(self.source2.owner_type, concept.owner_type)
        self.assertEquals(self.source2.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

    def test_persist_new_positive__earlier_source_version(self):
        version1 = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(version1.concepts))
        version2 = SourceVersion.for_base_object(self.source1, label='version2')
        version2.save()
        self.assertEquals(0, len(version2.concepts))

        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source1,
            'parent_resource_version': version1
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        version1 = SourceVersion.objects.get(id=version1.id)
        self.assertEquals(1, len(version1.concepts))
        self.assertTrue(concept_version.id in version1.concepts)

        version2 = SourceVersion.objects.get(id=version2.id)
        self.assertEquals(0, len(version2.concepts))
        self.assertFalse(concept_version.id in version2.concepts)

    def test_retire_positive(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(1, concept.num_versions)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(concept_version.is_latest_version)
        self.assertFalse(concept_version.retired)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(concept_version.id, source_version.concepts[0])

        errors = Concept.retire(concept, self.user1)
        self.assertFalse(errors)
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertTrue(concept.retired)
        self.assertEquals(2, concept.num_versions)

        previous_version = ConceptVersion.objects.get(id=concept_version.id)
        self.assertFalse(previous_version.is_latest_version)
        self.assertFalse(previous_version.retired)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(concept_version.is_latest_version)
        self.assertTrue(concept_version.retired)
        self.assertEquals(self.user1.username, concept_version.version_created_by)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(concept_version.id, source_version.concepts[0])

        self.assertEquals(
            1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=True).count())
        self.assertEquals(
            1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=False).count())

        errors = Concept.retire(concept, self.user1)
        self.assertEquals(1, len(errors))


class ConceptVersionTest(ConceptBaseTest):

    def setUp(self):
        super(ConceptVersionTest, self).setUp()
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
            locale='en',
        )
        self.concept1.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, self.user1, **kwargs)

        self.concept2 = Concept(
            mnemonic='concept2',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Second',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, self.user1, **kwargs)

    def test_create_concept_version_positive(self):
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            names=self.concept1.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
        )
        concept_version.full_clean()
        concept_version.save()
        self.assertTrue(ConceptVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            versioned_object_id=self.concept1.id,
        ).exists())
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        self.assertEquals(self.concept1.mnemonic, concept_version.name)
        self.assertEquals(self.concept1.owner_name, concept_version.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_version.owner_type)
        self.assertEquals(self.concept1.display_name, concept_version.display_name)
        self.assertEquals(self.concept1.display_locale, concept_version.display_locale)

    def test_create_concept_version_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                versioned_object=self.concept1,
                concept_class='First',
                names=[self.name],
            )
            concept_version.full_clean()
            concept_version.save()

    def test_create_concept_version_negative__no_versioned_object(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                mnemonic='version1',
                concept_class='First',
                names=[self.name],
            )
            concept_version.full_clean()
            concept_version.save()

    def test_create_concept_version_negative__no_concept_class(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                mnemonic='version1',
                versioned_object=self.concept1,
                names=[self.name],
            )
            concept_version.full_clean()
            concept_version.save()

    def test_concept_version_clone(self):
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            names=self.concept1.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
        )
        concept_version.full_clean()
        concept_version.save()
        self.assertTrue(ConceptVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            versioned_object_id=self.concept1.id,
        ).exists())
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        self.assertEquals(self.concept1.mnemonic, concept_version.name)
        self.assertEquals(self.concept1.owner_name, concept_version.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_version.owner_type)
        self.assertEquals(self.concept1.display_name, concept_version.display_name)
        self.assertEquals(self.concept1.display_locale, concept_version.display_locale)

        version2 = concept_version.clone()
        version2.mnemonic = 'version2'
        version2.created_by = self.user1.username
        version2.updated_by = self.user1.username
        version2.version_created_by = self.user1.username
        version2.full_clean()
        version2.save()

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(concept_version, version2.previous_version)
        self.assertEquals(concept_version.public_access, version2.public_access)

        self.assertEquals(self.concept1, version2.versioned_object)
        self.assertEquals(self.concept1.mnemonic, version2.name)
        self.assertEquals(self.concept1.owner_name, version2.owner_name)
        self.assertEquals(self.concept1.owner_type, version2.owner_type)
        self.assertEquals(self.concept1.display_name, version2.display_name)
        self.assertEquals(self.concept1.display_locale, version2.display_locale)

    def test_concept_version_inherits_public_access__positive(self):
        public_access = self.source1.public_access
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            public_access=public_access,
            names=self.concept1.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
        )
        concept_version.full_clean()
        concept_version.save()

        self.assertEquals(self.source1.public_access, concept_version.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

        self.assertNotEquals(public_access, self.source1.public_access)
        concept_version = ConceptVersion.objects.get(id=concept_version.id)
        self.assertEquals(self.source1.public_access, concept_version.public_access)

    def test_concept_version_all_names(self):
        concept_version = ConceptVersion.objects.get(versioned_object_id=self.concept1.id)
        expected_names_list = ['concept1', 'Fred']
        self.assertItemsEqual(concept_version.all_names, expected_names_list)

    def test_collections_ids(self):
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
            mnemonic='concept12',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)

        anotherConcept = Concept(
            mnemonic='anotherConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(anotherConcept, self.user1, **kwargs)

        another_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=anotherConcept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=concept1.mnemonic).mnemonic + '/'

        references = [concept1_reference, another_concept_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion.objects.get(versioned_object_id=Concept.objects.get(mnemonic=concept1.mnemonic).id)

        self.assertEquals(concept_version.collection_ids, [Collection.objects.get(mnemonic=collection.mnemonic).id])

    def test_collections_ids_with_multiple_concept_versions(self):
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
            mnemonic='concept12',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)
        initial_concept_version = ConceptVersion.objects.get(versioned_object_id=concept1.id)
        references = [concept1.uri, initial_concept_version.uri]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        ConceptVersion.persist_clone(initial_concept_version.clone(), self.user1)
        new_concept_version = ConceptVersion.objects.filter(versioned_object_id=concept1.id).order_by('-created_at')[0]

        self.assertEquals(initial_concept_version.collection_ids, [collection.id])
        self.assertEquals(new_concept_version.collection_ids, [Collection.objects.get(mnemonic=collection.mnemonic).id])

    def test_collections_ids_with_latest_concept_version(self):
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
            mnemonic='concept12',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)
        initial_concept_version = ConceptVersion.objects.get(versioned_object_id=concept1.id)
        ConceptVersion.persist_clone(initial_concept_version.clone(), self.user1)
        new_concept_version = ConceptVersion.objects.filter(versioned_object_id=concept1.id).order_by('-created_at')[0]

        collection.expressions = [new_concept_version.uri]
        collection.full_clean()
        collection.save()

        self.assertEquals(initial_concept_version.collection_ids, [])
        self.assertEquals(new_concept_version.collection_ids, [Collection.objects.get(mnemonic=collection.mnemonic).id])

    def test_collections_version_ids(self):
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
            mnemonic='concept12',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)

        another_concept = Concept(
            mnemonic='anotherConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es', type='FULLY_SPECIFIED')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(another_concept, self.user1, **kwargs)

        another_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=another_concept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=concept1.mnemonic).mnemonic + '/'

        references = [concept1_reference, another_concept_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion.objects.get(
            versioned_object_id=Concept.objects.get(mnemonic=another_concept.mnemonic).id)

        version = CollectionVersion.for_base_object(collection, 'version1')
        kwargs = {}
        CollectionVersion.persist_new(version, **kwargs)
        self.assertEquals(concept_version.collection_version_ids, [CollectionVersion.objects.get(mnemonic='version1').id])

class ConceptVersionStaticMethodsTest(ConceptBaseTest):

    def setUp(self):
        super(ConceptVersionStaticMethodsTest, self).setUp()
        self.concept1 = Concept(mnemonic='concept1', concept_class='First', public_access=ACCESS_TYPE_EDIT)
        display_name = LocalizedText(name='concept1', locale='en', type = 'FULLY_SPECIFIED')
        self.concept1.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, self.user1, **kwargs)
        initial_version = ConceptVersion.get_latest_version_of(self.concept1)

        self.concept2 = Concept(mnemonic='concept2', concept_class='Second', names=[self.name])
        kwargs = {
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, self.user1, **kwargs)

        self.concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            names=self.concept1.names,
            previous_version=initial_version,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
        )
        self.concept_version.full_clean()
        self.concept_version.save()

    def test_for_concept_positive(self):
        self.concept1.datatype = 'Boolean'
        self.concept1.save()

        label = 'version1'
        version = ConceptVersion.for_concept(self.concept1, label)

        self.assertEquals(label, version.mnemonic)
        self.assertEquals(self.concept1, version.versioned_object)
        self.assertEquals(self.concept1.concept_class, version.concept_class)
        self.assertEquals(self.concept1.datatype, version.datatype)
        self.assertEquals(self.concept1.names, version.names)
        self.assertEquals(self.concept1.descriptions, version.descriptions)
        self.assertEquals(self.concept1.retired, version.retired)
        self.assertEquals(self.concept1.public_access, version.public_access)
        self.assertEquals(self.concept1.external_id, version.external_id)
        self.assertFalse(version.released)

    def test_persist_clone_positive(self):
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        source_version = SourceVersion.get_latest_version_of(self.source1)

        source_version.update_concept_version(self.concept_version)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(self.concept_version.id, source_version.concepts[0])

        version2 = self.concept_version.clone()
        errors = ConceptVersion.persist_clone(version2, self.user1)
        self.assertEquals(0, len(errors))

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(self.concept_version.public_access, version2.public_access)
        self.assertEquals(self.concept_version, version2.previous_version)
        self.assertEquals(self.concept_version.root_version, version2.root_version)
        self.assertEquals(self.concept_version.external_id, version2.external_id)
        self.assertEquals(self.user1.username, version2.version_created_by)

        source_version.update_concept_version(version2)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(version2.id, source_version.concepts[0])

    def test_persist_clone_negative__no_user(self):
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        source_version = SourceVersion.get_latest_version_of(self.source1)

        source_version.update_concept_version(self.concept_version)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(self.concept_version.id, source_version.concepts[0])

        version2 = self.concept_version.clone()
        errors = ConceptVersion.persist_clone(version2)
        self.assertEquals(1, len(errors))
        self.assertTrue('version_created_by' in errors)

        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))


class ConceptVersionListViewTest(ConceptBaseTest):
    def test_get_csv_rows(self):
        concept = Concept(mnemonic='concept1', concept_class='First', public_access=ACCESS_TYPE_EDIT)
        display_name = LocalizedText(name='concept1', locale='en', type='FULLY_SPECIFIED')
        concept.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(concept, self.user1, **kwargs)
        concept_version = concept.get_latest_version

        view = ConceptVersionListView()
        view.kwargs = {}
        view.parent_resource_version = self.source1.get_head()
        view.child_list_attribute = 'concepts'
        csv_rows = view.get_csv_rows()
        self.assertEquals(len(csv_rows), 1)
        self.assertEquals(csv_rows[0].get('Retired'), False)
        self.assertEquals(csv_rows[0].get('Datatype'), None)
        self.assertEquals(csv_rows[0].get('Concept ID'), concept.mnemonic)
        self.assertEquals(csv_rows[0].get('External ID'), None)
        self.assertEquals(csv_rows[0].get('URI'), concept_version.uri)
        self.assertEquals(csv_rows[0].get('Synonyms'), 'concept1 [FULLY_SPECIFIED] [en]')

        # self.assertDictEqual(csv_rows[0], {'Retired': False, 'Datatype': None, 'Concept ID': concept.mnemonic, 'External ID': None, 'Description': '',
        #                                    'URI': concept_version.uri, 'Source': 'source1',
        #                                    'Synonyms': 'concept1 [FULLY_SPECIFIED] [en]', 'Last Updated': concept.created_at, 'Owner': 'org1',
        #                                    'Concept Class': concept_version.concept_class,'Preferred Name': '', 'Updated By': concept_version.created_by, 'Preferred Name Locale': ''})

class OpenMRSConceptValidationTest(ConceptBaseTest):

    def test_concept_should_have_exactly_one_preferred_name_per_locale(self):
        user = create_user()

        name_en1 = create_localized_text('PreferredName1')
        name_en1.locale_preferred = True

        name_en2 = create_localized_text('PreferredName2')
        name_en2.locale_preferred = True

        name_tr = create_localized_text('PreferredName3', locale="tr")
        name_tr.locale_preferred = True

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[name_en1, name_en2, name_tr],
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          'Custom validation rules require a concept to have exactly one preferred name')

    def test_concepts_should_have_unique_fully_specified_name_per_locale(self):
        user = create_user()

        name_fully_specified1 = create_localized_text('FullySpecifiedName1')
        description = create_localized_text("Description1")

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept1 = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[name_fully_specified1],
            descriptions=[description]
        )

        concept2 = Concept(
            mnemonic='EOCV',
            created_by=user,
            parent=source,
            concept_class='Second',
            names=[name_fully_specified1],
            descriptions=[description]
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept1, user, **kwargs)
        self.assertEquals(0, len(errors))

        errors = Concept.persist_new(concept2, user, **kwargs)
        self.assertEquals(errors['names'][0],
                          'Custom validation rules require fully specified name should be unique for same locale and source')


    def test_a_preferred_name_can_not_be_a_short_name(self):
        user = create_user()

        short_name = create_localized_text("ShortName")
        short_name.type = "SHORT"

        name = create_localized_text('ShortName')
        name.locale_preferred = True

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[short_name, name],
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          'Custom validation rules require a preferred name to be different than a short name')

    def test_a_preferred_name_can_not_be_an_index_search_term(self):
        user = create_user()

        name = create_localized_text("FullySpecifiedName")

        index_name = create_localized_text("IndexTermName")
        index_name.type = "INDEX_TERM"
        index_name.locale_preferred = True

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[name, index_name],
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          'Custom validation rules require a preferred name not to be an index/search term')

    def test_a_name_can_be_equal_to_a_short_name(self):
        user = create_user()

        name = create_localized_text("aName")

        short_name = create_localized_text("aName")
        short_name.type = "SHORT"

        description = create_localized_text("aDescription")

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[short_name, name],
            descriptions=[description]
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(0, len(errors))

    def test_a_name_should_be_unique(self):
        user = create_user()

        name = create_localized_text("aName")

        another_name = create_localized_text("aName")

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='EOPN',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[name, another_name],
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0], 'Custom validation rules require all names except type=SHORT to be unique')


    def test_must_have_at_least_one_description(self):
        user = create_user()

        name = create_localized_text("Name")

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        concept = Concept(
            mnemonic='TCPT',
            created_by=user,
            parent=source,
            concept_class='First',
            names=[name],
        )

        kwargs = {'parent_resource': source, }

        errors = Concept.persist_new(concept, user, **kwargs)

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['descriptions'][0], 'Custom validation rules require at least one description')