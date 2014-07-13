"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.test import TestCase
from concepts.models import Concept, LocalizedText, ConceptVersion
from orgs.models import Organization
from sources.models import Source, DICTIONARY_SRC_TYPE, EDIT_ACCESS_TYPE, REFERENCE_SRC_TYPE, VIEW_ACCESS_TYPE, SourceVersion
from users.models import UserProfile


class ConceptBaseTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(
            username='user1',
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
            source_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        Source.persist_new(self.source1, **kwargs)
        self.source1 = Source.objects.get(id=self.source1.id)

        self.source2 = Source(
            name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type=REFERENCE_SRC_TYPE,
            public_access=VIEW_ACCESS_TYPE,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.source2.com',
            description='This is the second test source'
        )
        kwargs = {
            'owner': self.user2,
            'parent_resource': self.org2,
        }
        Source.persist_new(self.source2, **kwargs)
        self.source2 = Source.objects.get(id=self.source2.id)


class ConceptTest(ConceptBaseTest):

    def test_create_concept_positive(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_create_concept_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                owner=self.user1,
                parent=self.source1,
                concept_class='First',
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                parent=self.source1,
                concept_class='First',
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                owner=self.user1,
                concept_class='First',
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_class(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                owner=self.user1,
                parent=self.source1,
            )
            concept.full_clean()
            concept.save()

    def test_concept_display_name(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en'
        )
        concept.names.append(display_name)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name.name, concept.display_name)
        self.assertEquals(display_name.locale, concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_concept_display_name_preferred(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        display_name1 = LocalizedText(
            name='concept1',
            locale='en',
            locale_preferred=True
        )
        concept.names.append(display_name1)
        display_name2 = LocalizedText(
            name='le concept1',
            locale='fr'
        )
        concept.names.append(display_name2)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name1.name, concept.display_name)
        self.assertEquals(display_name1.locale, concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)


class ConceptClassMethodsTest(ConceptBaseTest):

    def test_persist_new_positive(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

    def test_persist_new_negative__no_owner(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('owner' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.concepts))

    def test_persist_new_negative__no_parent(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'owner': self.user1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('parent' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.concepts))

    def test_persist_new_negative__repeated_mnemonic(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

        # Repeat with same mnemonic
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))

    def test_persist_new_positive__repeated_mnemonic(self):
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(concept_version.id in source_version.concepts)

        # Repeat with same mnemonic, different parent
        concept = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source2,
            concept_class='First',
        )
        source_version = SourceVersion.get_latest_version_of(self.source2)
        self.assertEquals(0, len(source_version.concepts))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source2,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source2.parent_resource, concept.owner_name)
        self.assertEquals(self.source2.parent_resource_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

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
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
            'parent_resource_version': version1
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertIsNone(concept.display_name)
        self.assertIsNone(concept.display_locale)
        self.assertEquals(self.source1.parent_resource, concept.owner_name)
        self.assertEquals(self.source1.parent_resource_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

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
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(concept, **kwargs)
        self.assertEquals(0, len(errors))

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(1, len(source_version.concepts))
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(1, concept.num_versions)

        retired = Concept.retire(concept)
        self.assertTrue(retired)
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertTrue(concept.retired)
        self.assertEquals(2, concept.num_versions)

        self.assertEquals(1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=True).count())
        self.assertEquals(1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=False).count())
        latest_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(latest_version.retired)
