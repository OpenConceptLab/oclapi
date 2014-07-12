"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.test import TestCase
from orgs.models import Organization
from sources.models import Source, DICTIONARY_SRC_TYPE, EDIT_ACCESS_TYPE, SourceVersion
from users.models import UserProfile


class SourceBaseTest(TestCase):
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


class SourceTest(SourceBaseTest):

    def test_create_source_positive(self):
        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.org1)
        source.full_clean()
        source.save()
        self.assertTrue(Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id)
        .exists())
        self.assertEquals(source.mnemonic, source.__unicode__())
        self.assertEquals(self.org1.mnemonic, source.parent_resource)
        self.assertEquals(self.org1.resource_type, source.parent_resource_type)

    def test_create_source_positive__valid_attributes(self):
        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1,
                        source_type=DICTIONARY_SRC_TYPE, public_access=EDIT_ACCESS_TYPE)
        source.full_clean()
        source.save()
        self.assertTrue(Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id
        ).exists())
        self.assertEquals(source.mnemonic, source.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, source.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, source.parent_resource_type)


    def test_create_source_positive__invalid_source_type(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1,
                            source_type='INVALID', public_access=EDIT_ACCESS_TYPE)
            source.full_clean()
            source.save()

    def test_create_source_positive__invalid_access_type(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1,
                            source_type=DICTIONARY_SRC_TYPE, public_access='INVALID')
            source.full_clean()
            source.save()

    def test_create_source_positive__valid_attributes(self):
        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1,
                        source_type=DICTIONARY_SRC_TYPE, public_access=EDIT_ACCESS_TYPE)
        source.full_clean()
        source.save()
        self.assertTrue(Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id)
        .exists())
        self.assertEquals(source.mnemonic, source.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, source.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, source.parent_resource_type)

    def test_create_source_negative__no_name(self):
        with self.assertRaises(ValidationError):
            source = Source(mnemonic='source1', owner=self.user1, parent=self.org1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', owner=self.user1, parent=self.org1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', parent=self.org1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', owner=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__mnemonic_exists(self):
        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.org1)
        source.full_clean()
        source.save()
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', owner=self.user2, parent=self.org1)
            source.full_clean()
            source.save()

    def test_create_positive__mnemonic_exists(self):
        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.org1)
        source.full_clean()
        source.save()
        self.assertEquals(1, Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id
        ).count())

        source = Source(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1)
        source.full_clean()
        source.save()
        self.assertEquals(1, Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id
        ).count())
        self.assertEquals(source.mnemonic, source.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, source.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, source.parent_resource_type)


class SourceVersionTest(SourceBaseTest):

    def setUp(self):
        super(SourceVersionTest, self).setUp()
        self.source1 = Source.objects.create(name='source1', mnemonic='source1', owner=self.user1, parent=self.org1)
        self.source2 = Source.objects.create(name='source1', mnemonic='source1', owner=self.user1, parent=self.userprofile1)

    def test_source_version_create_positive(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        source_version.full_clean()
        source_version.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())

        self.assertIsNone(source_version.previous_version)
        self.assertIsNone(source_version.previous_version_mnemonic)
        self.assertIsNone(source_version.parent_version)
        self.assertIsNone(source_version.parent_version_mnemonic)

        self.assertEquals(self.org1.mnemonic, source_version.parent_resource)
        self.assertEquals(self.org1.resource_type, source_version.parent_resource_type)

        self.assertEquals(source_version, SourceVersion.get_latest_version_of(self.source1))

    def test_source_version_create_negative__no_name(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                mnemonic='version1',
                versioned_object=self.source1
            )
            source_version.full_clean()
            source_version.save()

    def test_source_version_create_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                name='version1',
                versioned_object=self.source1
            )
            source_version.full_clean()
            source_version.save()

    def test_source_version_create_negative__no_source(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                mnemonic='version1',
                name='version1'
            )
            source_version.full_clean()
            source_version.save()

    def test_source_version_create_negative__same_mnemonic(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        source_version.full_clean()
        source_version.save()

        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                name='version1',
                mnemonic='version1',
                versioned_object=self.source1
            )
            source_version.full_clean()
            source_version.save()

    def test_source_version_create_positive__same_mnemonic(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        source_version.full_clean()
        source_version.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source2
        )
        source_version.full_clean()
        source_version.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source2.id
        ).exists())

    def test_source_version_create_positive__subsequent_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            previous_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals(version1.mnemonic, version2.previous_version_mnemonic)
        self.assertIsNone(version2.parent_version)
        self.assertIsNone(version2.parent_version_mnemonic)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            previous_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version2, version3.previous_version)
        self.assertEquals(version2.mnemonic, version3.previous_version_mnemonic)
        self.assertIsNone(version3.parent_version)
        self.assertIsNone(version3.parent_version_mnemonic)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))

    def test_source_version_create_positive__child_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            parent_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals(version1.mnemonic, version2.parent_version_mnemonic)
        self.assertIsNone(version2.previous_version)
        self.assertIsNone(version2.previous_version_mnemonic)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            parent_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals(version2.mnemonic, version3.parent_version_mnemonic)
        self.assertIsNone(version3.previous_version)
        self.assertIsNone(version3.previous_version_mnemonic)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))

    def test_source_version_create_positive__child_and_subsequent_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            parent_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals(version1.mnemonic, version2.parent_version_mnemonic)
        self.assertIsNone(version2.previous_version)
        self.assertIsNone(version2.previous_version_mnemonic)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            previous_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version2, version3.previous_version)
        self.assertEquals(version2.mnemonic, version3.previous_version_mnemonic)
        self.assertIsNone(version3.parent_version)
        self.assertIsNone(version3.parent_version_mnemonic)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))

    def test_source_version_create_positive__subsequent_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            previous_version=version1,
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals(version1.mnemonic, version2.previous_version_mnemonic)
        self.assertIsNone(version2.parent_version)
        self.assertIsNone(version2.parent_version_mnemonic)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            previous_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version2, version3.previous_version)
        self.assertEquals(version2.mnemonic, version3.previous_version_mnemonic)
        self.assertIsNone(version3.parent_version)
        self.assertIsNone(version3.parent_version_mnemonic)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))




class SourceVersionClassMethodTest(SourceBaseTest):

    def setUp(self):
        super(SourceVersionClassMethodTest, self).setUp()
        self.source1 = Source.objects.create(
            name='source1',
            mnemonic='source1',
            owner=self.user1,
            parent=self.org1,
            full_name='Source One',
            source_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )
        self.source2 = Source.objects.create(
            name='source1',
            mnemonic='source1',
            owner=self.user1,
            parent=self.userprofile1,
            full_name='Source Two',
            source_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.source2.com',
            description='This is the second test source'
        )

    def test_for_base_object_positive(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1')
        version1.full_clean()
        version1.save()
        self.assertEquals(version1.mnemonic, 'version1')
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(self.source1.name, version1.name)
        self.assertEquals(self.source1.full_name, version1.full_name)
        self.assertEquals(self.source1.source_type, version1.source_type)
        self.assertEquals(self.source1.public_access, version1.public_access)
        self.assertEquals(self.source1.default_locale, version1.default_locale)
        self.assertEquals(self.source1.supported_locales, version1.supported_locales)
        self.assertEquals(self.source1.website, version1.website)
        self.assertEquals(self.source1.description, version1.description)
        self.assertFalse(version1.released)
        self.assertIsNone(version1.parent_version)
        self.assertIsNone(version1.previous_version)

    def test_for_base_object_negative__no_source(self):
        with self.assertRaises(ValidationError):
            version1 = SourceVersion.for_base_object(None, 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__illegal_source(self):
        with self.assertRaises(ValidationError):
            version1 = SourceVersion.for_base_object(self.org1, 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__newborn_source(self):
        with self.assertRaises(ValidationError):
            version1 = SourceVersion.for_base_object(Source(), 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__bad_previous_version(self):
        with self.assertRaises(ValueError):
            version1 = SourceVersion.for_base_object(self.source1, 'version1', previous_version=self.source1)
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__bad_parent_version(self):
        with self.assertRaises(ValueError):
            version1 = SourceVersion.for_base_object(self.source1, 'version1', parent_version=self.source1)
            version1.full_clean()
            version1.save()



