"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.test import TestCase
from collection.models import CollectionVersion, Collection
from concepts.models import Concept, LocalizedText, ConceptVersion, ConceptReference
from orgs.models import Organization
from oclapi.models import EDIT_ACCESS_TYPE, VIEW_ACCESS_TYPE
from sources.models import Source, SourceVersion
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
            source_type='Dictionary',
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
            source_type='Reference',
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
        self.assertEquals(concept_version, concept_version.root_version)

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
        self.assertEquals(concept_version, concept_version.root_version)

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
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(1, concept.num_versions)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertFalse(concept_version.retired)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(concept_version.id, source_version.concepts[0])

        retired = Concept.retire(concept)
        self.assertTrue(retired)
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertTrue(concept.retired)
        self.assertEquals(2, concept.num_versions)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(concept_version.retired)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(concept_version.id, source_version.concepts[0])

        self.assertEquals(1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=True).count())
        self.assertEquals(1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=False).count())

        self.assertFalse(Concept.retire(concept))


class ConceptVersionTest(ConceptBaseTest):

    def setUp(self):
        super(ConceptVersionTest, self).setUp()
        self.concept1 = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en'
        )
        self.concept1.names.append(display_name)
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, **kwargs)

        self.concept2 = Concept(
            mnemonic='concept2',
            owner=self.user1,
            parent=self.source1,
            concept_class='Second',
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, **kwargs)

    def test_create_concept_version_positive(self):
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            names=self.concept1.names,
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
            )
            concept_version.full_clean()
            concept_version.save()

    def test_create_concept_version_negative__no_versioned_object(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                mnemonic='version1',
                concept_class='First',
            )
            concept_version.full_clean()
            concept_version.save()

    def test_create_concept_version_negative__no_concept_class(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                mnemonic='version1',
                versioned_object=self.concept1,
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
        version2.full_clean()
        version2.save()

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(concept_version, version2.previous_version)

        self.assertEquals(self.concept1, version2.versioned_object)
        self.assertEquals(self.concept1.mnemonic, version2.name)
        self.assertEquals(self.concept1.owner_name, version2.owner_name)
        self.assertEquals(self.concept1.owner_type, version2.owner_type)
        self.assertEquals(self.concept1.display_name, version2.display_name)
        self.assertEquals(self.concept1.display_locale, version2.display_locale)


class ConceptVersionStaticMethodsTest(ConceptBaseTest):

    def setUp(self):
        super(ConceptVersionStaticMethodsTest, self).setUp()
        self.concept1 = Concept(mnemonic='concept1', concept_class='First')
        display_name = LocalizedText(name='concept1', locale='en')
        self.concept1.names.append(display_name)
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, **kwargs)
        initial_version = ConceptVersion.get_latest_version_of(self.concept1)

        self.concept2 = Concept(mnemonic='concept2', concept_class='Second')
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, **kwargs)

        self.concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='First',
            names=self.concept1.names,
            previous_version=initial_version,
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
        self.assertFalse(version.released)

    def test_persist_clone_positive(self):
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        source_version = SourceVersion.get_latest_version_of(self.source1)

        source_version.update_concept_version(self.concept_version)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(self.concept_version.id, source_version.concepts[0])

        version2 = self.concept_version.clone()
        ConceptVersion.persist_clone(version2)

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(self.concept_version, version2.previous_version)
        self.assertEquals(self.concept_version.root_version, version2.root_version)

        source_version.update_concept_version(version2)
        self.assertEquals(1, len(source_version.concepts))
        self.assertEquals(version2.id, source_version.concepts[0])


class ConceptReferenceBaseTest(ConceptBaseTest):

    def setUp(self):
        super(ConceptReferenceBaseTest, self).setUp()
        self.concept1 = Concept(
            mnemonic='concept1',
            owner=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en'
        )
        self.concept1.names.append(display_name)
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, **kwargs)

        self.version1 = ConceptVersion.for_concept(self.concept1, 'version1')
        self.version1.save()

        self.concept2 = Concept(
            mnemonic='concept2',
            owner=self.user1,
            parent=self.source1,
            concept_class='Second',
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, **kwargs)
        self.version2 = ConceptVersion.for_concept(self.concept2, 'version2')
        self.version2.save()


class ConceptReferenceTest(ConceptReferenceBaseTest):

    def test_create_concept_reference_is_current__positive(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            parent=self.source1,
            mnemonic='reference1',
            concept=self.concept1
        )
        concept_reference.full_clean()
        concept_reference.save()

        self.assertTrue(ConceptReference.objects.filter(mnemonic='reference1').exists())
        self.assertEquals(self.concept1.concept_class, concept_reference.concept_class)
        self.assertEquals(self.concept1.datatype, concept_reference.data_type)
        self.assertEquals(self.concept1.parent, concept_reference.source)
        self.assertEquals(self.concept1.owner_name, concept_reference.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_reference.owner_type)
        self.assertEquals(self.concept1.display_name, concept_reference.display_name)
        self.assertEquals(self.concept1.display_locale, concept_reference.display_locale)
        self.assertEquals('/users/user1/sources/source1/concepts/concept1/', concept_reference.concept_reference_url)
        self.assertTrue(concept_reference.is_current_version)

    def test_create_concept_reference_concept_version__positive(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            parent=self.source1,
            mnemonic='reference1',
            concept=self.concept1,
            concept_version=self.version1
        )
        concept_reference.full_clean()
        concept_reference.save()

        self.assertTrue(ConceptReference.objects.filter(mnemonic='reference1').exists())
        self.assertEquals(self.concept1.concept_class, concept_reference.concept_class)
        self.assertEquals(self.concept1.datatype, concept_reference.data_type)
        self.assertEquals(self.concept1.parent, concept_reference.source)
        self.assertEquals(self.concept1.owner_name, concept_reference.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_reference.owner_type)
        self.assertEquals(self.concept1.display_name, concept_reference.display_name)
        self.assertEquals(self.concept1.display_locale, concept_reference.display_locale)
        self.assertEquals('/users/user1/sources/source1/concepts/concept1/version1/', concept_reference.concept_reference_url)
        self.assertFalse(concept_reference.is_current_version)

    def test_create_concept_reference_source_version__positive(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        concept_reference = ConceptReference(
            owner=self.user1,
            parent=self.source1,
            mnemonic='reference1',
            concept=self.concept1,
            source_version=source_version,
        )
        concept_reference.full_clean()
        concept_reference.save()

        self.assertTrue(ConceptReference.objects.filter(mnemonic='reference1').exists())
        self.assertEquals(self.concept1.concept_class, concept_reference.concept_class)
        self.assertEquals(self.concept1.datatype, concept_reference.data_type)
        self.assertEquals(self.concept1.parent, concept_reference.source)
        self.assertEquals(self.concept1.owner_name, concept_reference.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_reference.owner_type)
        self.assertEquals(self.concept1.display_name, concept_reference.display_name)
        self.assertEquals(self.concept1.display_locale, concept_reference.display_locale)
        self.assertEquals('/users/user1/sources/source1/%s/concepts/concept1/' % source_version.mnemonic, concept_reference.concept_reference_url)
        self.assertFalse(concept_reference.is_current_version)

    def test_create_concept_reference_concept_and_source_versions__negative(self):
        with self.assertRaises(ValidationError):
            concept_reference = ConceptReference(
                owner=self.user1,
                parent=self.source1,
                mnemonic='reference1',
                concept=self.concept1,
                concept_version=self.version1,
                source_version=SourceVersion.get_latest_version_of(self.source1)
            )
            concept_reference.full_clean()
            concept_reference.save()

    def test_create_concept_reference_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept = ConceptReference(
                owner=self.user1,
                parent=self.source1,
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_reference_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            concept = ConceptReference(
                mnemonic='concept1',
                parent=self.source1,
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_reference_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            concept = ConceptReference(
                mnemonic='concept1',
                owner=self.user1,
            )
            concept.full_clean()
            concept.save()


class ConceptReferenceClassMethodsTest(ConceptReferenceBaseTest):

    def setUp(self):
        super(ConceptReferenceClassMethodsTest, self).setUp()
        self.collection1 = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        Collection.persist_new(self.collection1, **kwargs)
        self.collection1 = Collection.objects.get(id=self.collection1.id)

        self.collection2 = Collection(
            name='collection2',
            mnemonic='collection2',
            full_name='Collection Two',
            collection_type='Dictionary',
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the second test collection'
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        Collection.persist_new(self.collection2, **kwargs)
        self.collection2 = Collection.objects.get(id=self.collection2.id)

    def test_persist_new_positive(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(1, len(collection_version.concept_references))
        self.assertTrue(concept_reference.id in collection_version.concept_references)

    def test_persist_new_negative__no_owner(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'parent_resource': self.collection1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('owner' in errors)

        self.assertFalse(ConceptReference.objects.filter(mnemonic='reference1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(0, len(collection_version.concept_references))


    def test_persist_new_negative__no_parent(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('parent' in errors)

        self.assertFalse(ConceptReference.objects.filter(mnemonic='reference1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(0, len(collection_version.concept_references))


    def test_persist_new_negative__no_child_list_attribute(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
        }
        with self.assertRaises(AttributeError):
            ConceptReference.persist_new(concept_reference, **kwargs)

        self.assertFalse(ConceptReference.objects.filter(mnemonic='reference1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(0, len(collection_version.concept_references))

    def test_persist_new_negative__repeated_mnemonic(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            parent=self.collection1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(1, len(collection_version.concept_references))
        self.assertTrue(concept_reference.id in collection_version.concept_references)

        # Repeat with same mnemonic
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection2)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)

        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(0, len(collection_version.concept_references))

    def test_persist_new_positive__repeated_mnemonic(self):
        concept_reference = ConceptReference(
            owner=self.user1,
            parent=self.collection1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(1, len(collection_version.concept_references))
        self.assertTrue(concept_reference.id in collection_version.concept_references)

        # Repeat with same mnemonic, different parent
        concept_reference = ConceptReference(
            owner=self.user1,
            mnemonic='reference1',
            concept=self.concept1
        )
        collection_version = CollectionVersion.get_latest_version_of(self.collection2)
        self.assertEquals(0, len(collection_version.concept_references))
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection2,
            'child_list_attribute': 'concept_references'
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        collection_version = CollectionVersion.objects.get(id=collection_version.id)
        self.assertEquals(1, len(collection_version.concept_references))
        self.assertTrue(concept_reference.id in collection_version.concept_references)

    def test_persist_new_positive__earlier_collection_version(self):
        version1 = CollectionVersion.get_latest_version_of(self.collection1)
        self.assertEquals(0, len(version1.concept_references))
        version2 = CollectionVersion.for_base_object(self.collection1, label='version2')
        version2.save()
        self.assertEquals(0, len(version2.concept_references))

        concept_reference = ConceptReference(
            mnemonic='concept1',
            owner=self.user1,
            concept=self.concept1,
        )
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.collection1,
            'parent_resource_version': version1,
            'child_list_attribute': 'concept_references',
        }
        errors = ConceptReference.persist_new(concept_reference, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(ConceptReference.objects.filter(mnemonic='concept1').exists())

        version1 = CollectionVersion.objects.get(id=version1.id)
        self.assertEquals(1, len(version1.concept_references))
        self.assertTrue(concept_reference.id in version1.concept_references)

        version2 = CollectionVersion.objects.get(id=version2.id)
        self.assertEquals(0, len(version2.concept_references))
        self.assertFalse(concept_reference.id in version2.concept_references)
