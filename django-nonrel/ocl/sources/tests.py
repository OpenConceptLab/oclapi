"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.test import TestCase
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from orgs.models import Organization
from sources.models import Source, SourceVersion
from concepts.models import Concept, LocalizedText, ConceptVersion
from users.models import UserProfile
from django.core.urlresolvers import reverse
import json

class SourceBaseTest(TestCase):
    def setUp(self):
        User.objects.filter().delete()
        UserProfile.objects.filter().delete()
        Organization.objects.filter().delete()
        Source.objects.filter().delete()
        SourceVersion.objects.filter().delete()
        Concept.objects.filter().delete()
        ConceptVersion.objects.filter().delete()

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
        self.name = LocalizedText.objects.create(name='Fred', locale='es')

    def tearDown(self):
        User.objects.filter().delete()
        UserProfile.objects.filter().delete()
        Organization.objects.filter().delete()
        Source.objects.filter().delete()
        Concept.objects.filter().delete()
        ConceptVersion.objects.filter().delete()
        SourceVersion.objects.filter().delete()

class SourceTest(SourceBaseTest):

    def test_create_source_positive(self):
        source = Source(name='source1', mnemonic='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
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
        self.assertEquals(0, source.num_versions)

    def test_create_source_positive__valid_attributes(self):
        source = Source(name='source1', mnemonic='source1', parent=self.userprofile1,
                        source_type='Dictionary', public_access=ACCESS_TYPE_EDIT, created_by=self.user1, updated_by=self.user1)
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
        self.assertEquals(0, source.num_versions)

    def test_create_source_negative__invalid_access_type(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', parent=self.userprofile1,
                            source_type='Dictionary', public_access='INVALID', created_by=self.user1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_positive__valid_attributes(self):
        source = Source(name='source1', mnemonic='source1', parent=self.userprofile1,
                        source_type='Dictionary', public_access=ACCESS_TYPE_EDIT, created_by=self.user1, updated_by=self.user1)
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
        self.assertEquals(0, source.num_versions)

    def test_create_source_negative__no_name(self):
        with self.assertRaises(ValidationError):
            source = Source(mnemonic='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_created_by(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', parent=self.org1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_updated_by(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', parent=self.org1, created_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', created_by=self.user1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_source_negative__mnemonic_exists(self):
        source = Source(name='source1', mnemonic='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
        source.full_clean()
        source.save()
        self.assertEquals(0, source.num_versions)
        with self.assertRaises(ValidationError):
            source = Source(name='source1', mnemonic='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
            source.full_clean()
            source.save()

    def test_create_positive__mnemonic_exists(self):
        source = Source(name='source1', mnemonic='source1', parent=self.org1, created_by=self.user1, updated_by=self.user1)
        source.full_clean()
        source.save()
        self.assertEquals(1, Source.objects.filter(
            mnemonic='source1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id
        ).count())
        self.assertEquals(0, source.num_versions)

        source = Source(name='source1', mnemonic='source1', parent=self.userprofile1, created_by=self.user1, updated_by=self.user1)
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
        self.assertEquals(0, source.num_versions)

class SourceClassMethodTest(SourceBaseTest):

    def setUp(self):
        super(SourceClassMethodTest, self).setUp()
        self.new_source = Source(
            name='source1',
            mnemonic='source1',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source'
        )

    def tearDown(self):
        super(SourceClassMethodTest, self).tearDown()

    def test_persist_new_positive(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Source.persist_new(self.new_source, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Source.objects.filter(name='source1').exists())
        source = Source.objects.get(name='source1')
        self.assertTrue(SourceVersion.objects.filter(versioned_object_id=source.id))
        source_version = SourceVersion.objects.get(versioned_object_id=source.id)
        self.assertEquals(1, source.num_versions)
        self.assertEquals(source_version, SourceVersion.get_latest_version_of(source))
        self.assertEquals(source_version.mnemonic, 'HEAD')
        self.assertFalse(source_version.released)

    def test_persist_new_negative__no_parent(self):
        errors = Source.persist_new(self.new_source, self.user1)
        self.assertTrue(errors.has_key('parent'))
        self.assertFalse(Source.objects.filter(name='source1').exists())

    def test_persist_new_negative__no_owner(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Source.persist_new(self.new_source, None, **kwargs)
        self.assertTrue(errors.has_key('created_by'))
        self.assertFalse(Source.objects.filter(name='source1').exists())

    def test_persist_new_negative__no_name(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        self.new_source.name = None
        errors = Source.persist_new(self.new_source, self.user1, **kwargs)
        self.assertTrue(errors.has_key('name'))
        self.assertFalse(Source.objects.filter(name='source1').exists())

    def test_persist_changes_positive(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Source.persist_new(self.new_source, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        id = self.new_source.id
        name = self.new_source.name
        mnemonic = self.new_source.mnemonic
        full_name = self.new_source.full_name
        source_type = self.new_source.source_type
        public_access = self.new_source.public_access
        default_locale = self.new_source.default_locale
        supported_locales = self.new_source.supported_locales
        website = self.new_source.website
        description = self.new_source.description

        self.new_source.name = "%s_prime" % name
        self.new_source.mnemonic = "%s-prime" % mnemonic
        self.new_source.full_name = "%s_prime" % full_name
        self.new_source.source_type = 'Reference'
        self.new_source.public_access = ACCESS_TYPE_VIEW
        self.new_source.default_locale = "%s_prime" % default_locale
        self.new_source.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_source.website = "%s_prime" % website
        self.new_source.description = "%s_prime" % description

        errors = Source.persist_changes(self.new_source, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Source.objects.filter(id=id).exists())
        self.assertTrue(SourceVersion.objects.filter(versioned_object_id=id))
        source_version = SourceVersion.objects.get(versioned_object_id=id)
        self.assertEquals(1, self.new_source.num_versions)
        self.assertEquals(source_version, SourceVersion.get_latest_version_of(self.new_source))

        self.new_source = Source.objects.get(id=id)
        self.assertNotEquals(name, self.new_source.name)
        self.assertNotEquals(mnemonic, self.new_source.mnemonic)
        self.assertNotEquals(full_name, self.new_source.full_name)
        self.assertNotEquals(source_type, self.new_source.source_type)
        self.assertNotEquals(public_access, self.new_source.public_access)
        self.assertNotEquals(default_locale, self.new_source.default_locale)
        self.assertNotEquals(supported_locales, self.new_source.supported_locales)
        self.assertNotEquals(website, self.new_source.website)
        self.assertNotEquals(description, self.new_source.description)

    def test_persist_changes_negative__repeated_mnemonic(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Source.persist_new(self.new_source, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        source = Source(
            name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source2.com',
            description='This is the second test source'
        )
        errors = Source.persist_new(source, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertEquals(2, Source.objects.all().count())

        self.new_source = Source.objects.get(mnemonic='source2')
        id = self.new_source.id
        name = self.new_source.name
        mnemonic = self.new_source.mnemonic
        full_name = self.new_source.full_name
        source_type = self.new_source.source_type
        public_access = self.new_source.public_access
        default_locale = self.new_source.default_locale
        supported_locales = self.new_source.supported_locales
        website = self.new_source.website
        description = self.new_source.description

        self.new_source.mnemonic = 'source1'
        self.new_source.name = "%s_prime" % name
        self.new_source.full_name = "%s_prime" % full_name
        self.new_source.source_type = 'Reference'
        self.new_source.public_access = ACCESS_TYPE_VIEW
        self.new_source.default_locale = "%s_prime" % default_locale
        self.new_source.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_source.website = "%s_prime" % website
        self.new_source.description = "%s_prime" % description

        errors = Source.persist_changes(self.new_source, self.user1, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue(errors.has_key('__all__'))
        self.assertTrue(Source.objects.filter(id=id).exists())
        self.assertTrue(SourceVersion.objects.filter(versioned_object_id=id))
        source_version = SourceVersion.objects.get(versioned_object_id=id)
        self.assertEquals(1, self.new_source.num_versions)
        self.assertEquals(source_version, SourceVersion.get_latest_version_of(self.new_source))

        self.new_source = Source.objects.get(id=id)
        self.assertEquals(name, self.new_source.name)
        self.assertEquals(mnemonic, self.new_source.mnemonic)
        self.assertEquals(full_name, self.new_source.full_name)
        self.assertEquals(source_type, self.new_source.source_type)
        self.assertEquals(public_access, self.new_source.public_access)
        self.assertEquals(default_locale, self.new_source.default_locale)
        self.assertEquals(supported_locales, self.new_source.supported_locales)
        self.assertEquals(website, self.new_source.website)
        self.assertEquals(description, self.new_source.description)


class SourceVersionTest(SourceBaseTest):

    def setUp(self):
        super(SourceVersionTest, self).setUp()
        self.source1 = Source.objects.create(name='source1', mnemonic='source1', parent=self.org1)
        self.source2 = Source.objects.create(name='source1', mnemonic='source1', parent=self.userprofile1)

    def test_source_version_create_positive(self):
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
        self.assertEquals(1, self.source1.num_versions)

    def test_source_version_create_negative__no_name(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                mnemonic='version1',
                versioned_object=self.source1,
                created_by=self.user1,
                updated_by=self.user1,

            )
            source_version.full_clean()
            source_version.save()
        self.assertEquals(0, self.source1.num_versions)

    def test_source_version_create_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                name='version1',
                versioned_object=self.source1,
                created_by=self.user1,
                updated_by=self.user1,
            )
            source_version.full_clean()
            source_version.save()
        self.assertEquals(0, self.source1.num_versions)

    def test_source_version_create_negative__no_source(self):
        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                mnemonic='version1',
                name='version1',
                created_by=self.user1,
                updated_by=self.user1,
            )
            source_version.full_clean()
            source_version.save()
        self.assertEquals(0, self.source1.num_versions)

    def test_source_version_create_negative__same_mnemonic(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            created_by=self.user1,
            updated_by=self.user1,

        )
        source_version.full_clean()
        source_version.save()
        self.assertEquals(1, self.source1.num_versions)

        with self.assertRaises(ValidationError):
            source_version = SourceVersion(
                name='version1',
                mnemonic='version1',
                versioned_object=self.source1,
                created_by=self.user1,
                updated_by=self.user1,

            )
            source_version.full_clean()
            source_version.save()
        self.assertEquals(1, self.source1.num_versions)

    def test_source_version_create_positive__same_mnemonic(self):
        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(1, self.source1.num_versions)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source2,
            created_by=self.user1,
            updated_by=self.user1,
        )
        source_version.full_clean()
        source_version.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source2.id
        ).exists())
        self.assertEquals(1, self.source2.num_versions)

    def test_source_version_create_positive__subsequent_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(1, self.source1.num_versions)

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            previous_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEqual(2, self.source1.num_versions)

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            previous_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEquals(3, self.source1.num_versions)

    def test_source_version_create_positive__child_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(1, self.source1.num_versions)

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            parent_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEquals(2, self.source1.num_versions)

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            parent_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEquals(3, self.source1.num_versions)

    def test_source_version_create_positive__child_and_subsequent_versions(self):
        version1 = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(SourceVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Source),
            versioned_object_id=self.source1.id
        ).exists())
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(1, self.source1.num_versions)

        version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            parent_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEquals(2, self.source1.num_versions)

        version3 = SourceVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.source1,
            previous_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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
        self.assertEquals(3, self.source1.num_versions)

    def test_seed_concepts(self):
        concept1 = Concept(mnemonic='concept1', created_by=self.user1, parent=self.source1, concept_class='First', names=[self.name])
        concept2 = Concept(mnemonic='concept2', created_by=self.user1, parent=self.source1, concept_class='Second', names=[self.name])

        head = SourceVersion(name='head', mnemonic='HEAD', versioned_object=self.source1, released=True, created_by=self.user1, updated_by=self.user1)
        head.full_clean()
        head.save()


        kwargs = {'parent_resource': self.source1}

        Concept.persist_new(concept1, self.user1, **kwargs)
        version1 = SourceVersion(name='version1', mnemonic='v1', versioned_object=self.source1, released=True, created_by=self.user1, updated_by=self.user1)
        SourceVersion.persist_new(version1)

        Concept.persist_new(concept2, self.user1, **kwargs)

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertTrue(Concept.objects.filter(mnemonic='concept2').exists())
        self.assertEquals(len(SourceVersion.objects.get(id=head.id).concepts), 2)
        self.assertEquals(len(SourceVersion.objects.get(mnemonic=version1.mnemonic).concepts), 1)

        source_version2 = SourceVersion(name='version2', mnemonic='version2', versioned_object=self.source1, released=True, created_by=self.user1, updated_by=self.user1)

        source_version2.seed_concepts

        self.assertEquals(source_version2.concepts, head.concepts)

    def test_head_sibling(self):
        source_version1 = SourceVersion(
            name='head',
            mnemonic='HEAD',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )

        source_version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.source1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )

        source_version1.full_clean()
        source_version1.save()
        source_version2.full_clean()
        source_version2.save()

        self.assertEquals(source_version1.head_sibling(), source_version1)
        self.assertEquals(source_version2.head_sibling(), source_version1)

class SourceVersionClassMethodTest(SourceBaseTest):

    def setUp(self):
        super(SourceVersionClassMethodTest, self).setUp()
        self.source1 = Source.objects.create(
            name='source1',
            mnemonic='source1',
            parent=self.org1,
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source1.com',
            description='This is the first test source',
            created_by=self.user1,
            updated_by=self.user1,
            external_id='EXTID1',
        )
        self.source2 = Source.objects.create(
            name='source1',
            mnemonic='source1',
            parent=self.userprofile1,
            full_name='Source Two',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.source2.com',
            description='This is the second test source',
            created_by=self.user1,
            updated_by=self.user1,
            external_id='EXTID2',
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
        self.assertEquals(self.source1.external_id, version1.external_id)
        self.assertFalse(version1.released)
        self.assertIsNone(version1.parent_version)
        self.assertIsNone(version1.previous_version)
        self.assertEquals(1, self.source1.num_versions)

    def test_for_base_object_initial_positive(self):
        version1 = SourceVersion.for_base_object(self.source1, 'INITIAL')
        version1.full_clean()
        version1.save()
        self.assertEquals(version1.mnemonic, 'HEAD')
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(self.source1.name, version1.name)
        self.assertEquals(self.source1.full_name, version1.full_name)
        self.assertEquals(self.source1.source_type, version1.source_type)
        self.assertEquals(self.source1.public_access, version1.public_access)
        self.assertEquals(self.source1.default_locale, version1.default_locale)
        self.assertEquals(self.source1.supported_locales, version1.supported_locales)
        self.assertEquals(self.source1.website, version1.website)
        self.assertEquals(self.source1.description, version1.description)
        self.assertEquals(self.source1.external_id, version1.external_id)
        self.assertFalse(version1.released)
        self.assertIsNone(version1.parent_version)
        self.assertIsNone(version1.previous_version)
        self.assertEquals(1, self.source1.num_versions)

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
        self.assertEquals(0, self.source1.num_versions)

    def test_for_base_object_negative__bad_parent_version(self):
        with self.assertRaises(ValueError):
            version1 = SourceVersion.for_base_object(self.source1, 'version1', parent_version=self.source1)
            version1.full_clean()
            version1.save()
        self.assertEquals(0, self.source1.num_versions)

    def test_persist_changes_positive(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1')
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description
        external_id = version1.external_id

        id = version1.id
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version1)
        self.assertEquals(0, len(errors))

        version1 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(1, self.source1.num_versions)
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertNotEquals(mnemonic, version1.mnemonic)
        self.assertNotEquals(released, version1.released)
        self.assertNotEquals(description, version1.description)
        self.assertNotEquals(external_id, version1.external_id)

    def test_persist_changes_negative__bad_previous_version(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description
        external_id = version1.external_id

        id = version1.id
        version1._previous_version_mnemonic = 'No such version'
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('previousVersion' in errors)

        version1 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(1, self.source1.num_versions)
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__previous_version_is_self(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description
        external_id = version1.external_id

        id = version1.id
        version1._previous_version_mnemonic = mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('previousVersion' in errors)

        version1 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(1, self.source1.num_versions)
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__bad_parent_version(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description
        external_id = version1.external_id

        id = version1.id
        version1._parent_version_mnemonic = 'No such version'
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('parentVersion' in errors)

        version1 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(1, self.source1.num_versions)
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__parent_version_is_self(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description
        external_id = version1.external_id

        id = version1.id
        version1._parent_version_mnemonic = mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('parentVersion' in errors)

        version1 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version1.versioned_object)
        self.assertEquals(1, self.source1.num_versions)
        self.assertEquals(version1, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_positive__good_previous_version(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1')
        version1.full_clean()
        version1.save()

        version2 = SourceVersion.for_base_object(self.source1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description
        external_id = version2.external_id

        id = version2.id
        version2._previous_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.previous_version)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)
        self.assertNotEquals(external_id, version2.external_id)

    def test_persist_changes_positive__good_parent_version(self):
        version1 = SourceVersion.for_base_object(self.source1, 'version1')
        version1.full_clean()
        version1.save()

        version2 = SourceVersion.for_base_object(self.source1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.parent_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description
        external_id = version2.external_id

        id = version2.id
        version2._parent_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.parent_version)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)
        self.assertNotEquals(external_id, version2.external_id)

    def test_persist_changes_positive__seed_from_previous(self):
        version1 = SourceVersion.for_base_object(self.source1, 'INITIAL')
        version1.concepts = [1]
        version1.full_clean()
        version1.save()

        version2 = SourceVersion.for_base_object(self.source1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description
        external_id = version2.external_id

        id = version2.id
        version2._previous_version_mnemonic = version1.mnemonic
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals([], version2.concepts)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)
        self.assertNotEquals(external_id, version2.external_id)

        errors = SourceVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals([1], version2.concepts)

    def test_persist_changes_positive__seed_from_parent(self):
        version1 = SourceVersion.for_base_object(self.source1, 'INITIAL')
        version1.concepts = [2]
        version1.full_clean()
        version1.save()

        version2 = SourceVersion.for_base_object(self.source1, 'version1')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.parent_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description
        external_id = version2.external_id

        id = version2.id
        version2._parent_version_mnemonic = version1.mnemonic
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals([], version2.concepts)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)
        self.assertNotEquals(external_id, version2.external_id)

        errors = SourceVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version2.versioned_object)
        self.assertEquals(2, self.source1.num_versions)
        self.assertEquals(version2, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals([2], version2.concepts)

    def test_persist_changes_positive__seed_from_previous_over_parent(self):
        version1 = SourceVersion.for_base_object(self.source1, 'INITIAL')
        version1.concepts = [1]
        version1.full_clean()
        version1.save()

        version2 = SourceVersion.for_base_object(self.source1, 'version2')
        version2.concepts = [2]
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        version3 = SourceVersion.for_base_object(self.source1, 'version3')
        version3.full_clean()
        version3.save()

        mnemonic = version3.mnemonic
        released = version3.released
        description = version3.description
        external_id = version3.external_id

        id = version3.id
        version3._parent_version_mnemonic = 'version2'
        version3._previous_version_mnemonic = version1.mnemonic
        version3.mnemonic = "%s-prime" % mnemonic
        version3.released = not released
        version3.description = "%s-prime" % description
        version3.external_id = "%s-prime" % external_id

        errors = SourceVersion.persist_changes(version3)
        self.assertEquals(0, len(errors))

        version3 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version3.versioned_object)
        self.assertEquals(3, self.source1.num_versions)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version1, version3.previous_version)
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals([], version3.concepts)
        self.assertNotEquals(mnemonic, version3.mnemonic)
        self.assertNotEquals(released, version3.released)
        self.assertNotEquals(description, version3.description)
        self.assertNotEquals(external_id, version3.external_id)

        errors = SourceVersion.persist_changes(version3, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version3 = SourceVersion.objects.get(id=id)
        self.assertEquals(self.source1, version3.versioned_object)
        self.assertEquals(3, self.source1.num_versions)
        self.assertEquals(version3, SourceVersion.get_latest_version_of(self.source1))
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals(version1, version3.previous_version)
        self.assertEquals([1], version3.concepts)

class SourceVersionListViewTest(SourceBaseTest):

    def test_get(self):
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
        source = Source.objects.get(id=source.id)

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
            public_access='Edit'
        )
        source_version.full_clean()
        source_version.save()

        concept = Concept(
            mnemonic='concept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='not First',
            external_id='EXTID',
            names=[self.name],
        )
        display_name = LocalizedText(
            name='concept',
            locale='en'
        )
        concept.names.append(display_name)
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept, self.user1, **kwargs)


        kwargs = {'org': self.org1.mnemonic, 'source': source.mnemonic}

        response = self.client.get(reverse('sourceversion-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEquals(2,len(content))
        self.assertEquals(content[0]['id'], 'HEAD')



