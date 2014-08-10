"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.test import TestCase
from collection.models import Collection, CollectionVersion
from oclapi.models import EDIT_ACCESS_TYPE, VIEW_ACCESS_TYPE
from orgs.models import Organization
from sources.models import DICTIONARY_SRC_TYPE, REFERENCE_SRC_TYPE
from users.models import UserProfile


class CollectionBaseTest(TestCase):
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


class CollectionTest(CollectionBaseTest):

    def test_create_collection_positive(self):
        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.org1)
        collection.full_clean()
        collection.save()
        self.assertTrue(Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id)
        .exists())
        self.assertEquals(collection.mnemonic, collection.__unicode__())
        self.assertEquals(self.org1.mnemonic, collection.parent_resource)
        self.assertEquals(self.org1.resource_type, collection.parent_resource_type)
        self.assertEquals(0, collection.num_versions)

    def test_create_collection_positive__valid_attributes(self):
        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.userprofile1,
                        collection_type=DICTIONARY_SRC_TYPE, public_access=EDIT_ACCESS_TYPE)
        collection.full_clean()
        collection.save()
        self.assertTrue(Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id
        ).exists())
        self.assertEquals(collection.mnemonic, collection.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, collection.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, collection.parent_resource_type)
        self.assertEquals(0, collection.num_versions)

    def test_create_collection_negative__invalid_access_type(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.userprofile1,
                            collection_type=DICTIONARY_SRC_TYPE, public_access='INVALID')
            collection.full_clean()
            collection.save()

    def test_create_collection_positive__valid_attributes(self):
        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.userprofile1,
                        collection_type=DICTIONARY_SRC_TYPE, public_access=EDIT_ACCESS_TYPE)
        collection.full_clean()
        collection.save()
        self.assertTrue(Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id)
        .exists())
        self.assertEquals(collection.mnemonic, collection.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, collection.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, collection.parent_resource_type)
        self.assertEquals(0, collection.num_versions)

    def test_create_collection_negative__no_name(self):
        with self.assertRaises(ValidationError):
            collection = Collection(mnemonic='collection1', owner=self.user1, parent=self.org1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', owner=self.user1, parent=self.org1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', parent=self.org1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__mnemonic_exists(self):
        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.org1)
        collection.full_clean()
        collection.save()
        self.assertEquals(0, collection.num_versions)
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', owner=self.user2, parent=self.org1)
            collection.full_clean()
            collection.save()

    def test_create_positive__mnemonic_exists(self):
        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.org1)
        collection.full_clean()
        collection.save()
        self.assertEquals(1, Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id
        ).count())
        self.assertEquals(0, collection.num_versions)

        collection = Collection(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.userprofile1)
        collection.full_clean()
        collection.save()
        self.assertEquals(1, Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(UserProfile),
            parent_id=self.userprofile1.id
        ).count())
        self.assertEquals(collection.mnemonic, collection.__unicode__())
        self.assertEquals(self.userprofile1.mnemonic, collection.parent_resource)
        self.assertEquals(self.userprofile1.resource_type, collection.parent_resource_type)
        self.assertEquals(0, collection.num_versions)


class CollectionClassMethodTest(CollectionBaseTest):

    def setUp(self):
        super(CollectionClassMethodTest, self).setUp()
        self.new_collection = Collection(
            name='collection1',
            mnemonic='collection1',
            full_name='Collection One',
            collection_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )

    def test_persist_new_positive(self):
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Collection.objects.filter(name='collection1').exists())
        collection = Collection.objects.get(name='collection1')
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=collection.id))
        collection_version = CollectionVersion.objects.get(versioned_object_id=collection.id)
        self.assertEquals(1, collection.num_versions)
        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(collection))

    def test_persist_new_negative__no_parent(self):
        kwargs = {
            'owner': self.user1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertTrue(errors.has_key('parent'))
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_new_negative__no_owner(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertTrue(errors.has_key('owner'))
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_new_negative__no_name(self):
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        self.new_collection.name = None
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertTrue(errors.has_key('name'))
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_changes_positive(self):
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertEquals(0, len(errors))

        id = self.new_collection.id
        name = self.new_collection.name
        mnemonic = self.new_collection.mnemonic
        full_name = self.new_collection.full_name
        collection_type = self.new_collection.collection_type
        public_access = self.new_collection.public_access
        default_locale = self.new_collection.default_locale
        supported_locales = self.new_collection.supported_locales
        website = self.new_collection.website
        description = self.new_collection.description

        self.new_collection.name = "%s_prime" % name
        self.new_collection.mnemonic = "%s-prime" % mnemonic
        self.new_collection.full_name = "%s_prime" % full_name
        self.new_collection.collection_type = REFERENCE_SRC_TYPE
        self.new_collection.public_access = VIEW_ACCESS_TYPE
        self.new_collection.default_locale = "%s_prime" % default_locale
        self.new_collection.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_collection.website = "%s_prime" % website
        self.new_collection.description = "%s_prime" % description

        del(kwargs['owner'])
        errors = Collection.persist_changes(self.new_collection, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Collection.objects.filter(id=id).exists())
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=id))
        collection_version = CollectionVersion.objects.get(versioned_object_id=id)
        self.assertEquals(1, self.new_collection.num_versions)
        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(self.new_collection))

        self.new_collection = Collection.objects.get(id=id)
        self.assertNotEquals(name, self.new_collection.name)
        self.assertNotEquals(mnemonic, self.new_collection.mnemonic)
        self.assertNotEquals(full_name, self.new_collection.full_name)
        self.assertNotEquals(collection_type, self.new_collection.collection_type)
        self.assertNotEquals(public_access, self.new_collection.public_access)
        self.assertNotEquals(default_locale, self.new_collection.default_locale)
        self.assertNotEquals(supported_locales, self.new_collection.supported_locales)
        self.assertNotEquals(website, self.new_collection.website)
        self.assertNotEquals(description, self.new_collection.description)

    def test_persist_changes_negative__illegal_value(self):
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertEquals(0, len(errors))

        id = self.new_collection.id
        name = self.new_collection.name
        mnemonic = self.new_collection.mnemonic
        full_name = self.new_collection.full_name
        collection_type = self.new_collection.collection_type
        public_access = self.new_collection.public_access
        default_locale = self.new_collection.default_locale
        supported_locales = self.new_collection.supported_locales
        website = self.new_collection.website
        description = self.new_collection.description

        self.new_collection.name = "%s_prime" % name
        self.new_collection.mnemonic = "%s_prime" % mnemonic
        self.new_collection.full_name = "%s_prime" % full_name
        self.new_collection.collection_type = "%s_prime" % collection_type
        self.new_collection.public_access = "%s_prime" % public_access
        self.new_collection.default_locale = "%s_prime" % default_locale
        self.new_collection.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_collection.website = "%s_prime" % website
        self.new_collection.description = "%s_prime" % description

        del(kwargs['owner'])
        errors = Collection.persist_changes(self.new_collection, **kwargs)
        self.assertTrue(Collection.objects.filter(id=id).exists())
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=id))
        collection_version = CollectionVersion.objects.get(versioned_object_id=id)
        self.assertEquals(1, self.new_collection.num_versions)
        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(self.new_collection))

        self.new_collection = Collection.objects.get(id=id)
        self.assertEquals(name, self.new_collection.name)
        self.assertEquals(mnemonic, self.new_collection.mnemonic)
        self.assertEquals(full_name, self.new_collection.full_name)
        self.assertEquals(collection_type, self.new_collection.collection_type)
        self.assertEquals(public_access, self.new_collection.public_access)
        self.assertEquals(default_locale, self.new_collection.default_locale)
        self.assertEquals(supported_locales, self.new_collection.supported_locales)
        self.assertEquals(website, self.new_collection.website)
        self.assertEquals(description, self.new_collection.description)

    def test_persist_changes_negative__repeated_mnemonic(self):
        kwargs = {
            'owner': self.user1,
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, **kwargs)
        self.assertEquals(0, len(errors))

        collection = Collection(
            name='collection2',
            mnemonic='collection2',
            full_name='Collection Two',
            collection_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection2.com',
            description='This is the second test collection'
        )
        errors = Collection.persist_new(collection, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertEquals(2, Collection.objects.all().count())

        self.new_collection = Collection.objects.get(mnemonic='collection2')
        id = self.new_collection.id
        name = self.new_collection.name
        mnemonic = self.new_collection.mnemonic
        full_name = self.new_collection.full_name
        collection_type = self.new_collection.collection_type
        public_access = self.new_collection.public_access
        default_locale = self.new_collection.default_locale
        supported_locales = self.new_collection.supported_locales
        website = self.new_collection.website
        description = self.new_collection.description

        self.new_collection.mnemonic = 'collection1'
        self.new_collection.name = "%s_prime" % name
        self.new_collection.full_name = "%s_prime" % full_name
        self.new_collection.collection_type = REFERENCE_SRC_TYPE
        self.new_collection.public_access = VIEW_ACCESS_TYPE
        self.new_collection.default_locale = "%s_prime" % default_locale
        self.new_collection.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_collection.website = "%s_prime" % website
        self.new_collection.description = "%s_prime" % description

        del(kwargs['owner'])
        errors = Collection.persist_changes(self.new_collection, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue(errors.has_key('__all__'))
        self.assertTrue(Collection.objects.filter(id=id).exists())
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=id))
        collection_version = CollectionVersion.objects.get(versioned_object_id=id)
        self.assertEquals(1, self.new_collection.num_versions)
        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(self.new_collection))

        self.new_collection = Collection.objects.get(id=id)
        self.assertEquals(name, self.new_collection.name)
        self.assertEquals(mnemonic, self.new_collection.mnemonic)
        self.assertEquals(full_name, self.new_collection.full_name)
        self.assertEquals(collection_type, self.new_collection.collection_type)
        self.assertEquals(public_access, self.new_collection.public_access)
        self.assertEquals(default_locale, self.new_collection.default_locale)
        self.assertEquals(supported_locales, self.new_collection.supported_locales)
        self.assertEquals(website, self.new_collection.website)
        self.assertEquals(description, self.new_collection.description)


class CollectionVersionTest(CollectionBaseTest):

    def setUp(self):
        super(CollectionVersionTest, self).setUp()
        self.collection1 = Collection.objects.create(name='collection1', mnemonic='collection1', owner=self.user1, parent=self.org1)
        self.collection2 = Collection.objects.create(name='collection2', mnemonic='collection2', owner=self.user1, parent=self.userprofile1)

    def test_collection_version_create_positive(self):
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            released=True
        )
        collection_version.full_clean()
        collection_version.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())

        self.assertIsNone(collection_version.previous_version)
        self.assertIsNone(collection_version.previous_version_mnemonic)
        self.assertIsNone(collection_version.parent_version)
        self.assertIsNone(collection_version.parent_version_mnemonic)

        self.assertEquals(self.org1.mnemonic, collection_version.parent_resource)
        self.assertEquals(self.org1.resource_type, collection_version.parent_resource_type)

        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(1, self.collection1.num_versions)

    def test_collection_version_create_negative__no_name(self):
        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                mnemonic='version1',
                versioned_object=self.collection1
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                name='version1',
                versioned_object=self.collection1
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__no_collection(self):
        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                mnemonic='version1',
                name='version1'
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__same_mnemonic(self):
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1
        )
        collection_version.full_clean()
        collection_version.save()
        self.assertEquals(1, self.collection1.num_versions)

        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                name='version1',
                mnemonic='version1',
                versioned_object=self.collection1
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(1, self.collection1.num_versions)

    def test_collection_version_create_positive__same_mnemonic(self):
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1
        )
        collection_version.full_clean()
        collection_version.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(1, self.collection1.num_versions)

        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection2
        )
        collection_version.full_clean()
        collection_version.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection2.id
        ).exists())
        self.assertEquals(1, self.collection2.num_versions)

    def test_collection_version_create_positive__subsequent_versions(self):
        version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            released=True
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(1, self.collection1.num_versions)

        version2 = CollectionVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.collection1,
            previous_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals(version1.mnemonic, version2.previous_version_mnemonic)
        self.assertIsNone(version2.parent_version)
        self.assertIsNone(version2.parent_version_mnemonic)
        self.assertEqual(2, self.collection1.num_versions)

        version3 = CollectionVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.collection1,
            previous_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version2, version3.previous_version)
        self.assertEquals(version2.mnemonic, version3.previous_version_mnemonic)
        self.assertIsNone(version3.parent_version)
        self.assertIsNone(version3.parent_version_mnemonic)
        self.assertEquals(3, self.collection1.num_versions)

    def test_collection_version_create_positive__child_versions(self):
        version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            released=True
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(1, self.collection1.num_versions)

        version2 = CollectionVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.collection1,
            parent_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals(version1.mnemonic, version2.parent_version_mnemonic)
        self.assertIsNone(version2.previous_version)
        self.assertIsNone(version2.previous_version_mnemonic)
        self.assertEquals(2, self.collection1.num_versions)

        version3 = CollectionVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.collection1,
            parent_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals(version2.mnemonic, version3.parent_version_mnemonic)
        self.assertIsNone(version3.previous_version)
        self.assertIsNone(version3.previous_version_mnemonic)
        self.assertEquals(3, self.collection1.num_versions)

    def test_collection_version_create_positive__child_and_subsequent_versions(self):
        version1 = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            released=True
        )
        version1.full_clean()
        version1.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(1, self.collection1.num_versions)

        version2 = CollectionVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=self.collection1,
            parent_version=version1
        )
        version2.full_clean()
        version2.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version2',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals(version1.mnemonic, version2.parent_version_mnemonic)
        self.assertIsNone(version2.previous_version)
        self.assertIsNone(version2.previous_version_mnemonic)
        self.assertEquals(2, self.collection1.num_versions)

        version3 = CollectionVersion(
            name='version3',
            mnemonic='version3',
            versioned_object=self.collection1,
            previous_version=version2
        )
        version3.full_clean()
        version3.save()
        self.assertTrue(CollectionVersion.objects.filter(
            mnemonic='version3',
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            versioned_object_id=self.collection1.id
        ).exists())
        self.assertEquals(version2, version3.previous_version)
        self.assertEquals(version2.mnemonic, version3.previous_version_mnemonic)
        self.assertIsNone(version3.parent_version)
        self.assertIsNone(version3.parent_version_mnemonic)
        self.assertEquals(3, self.collection1.num_versions)


class CollectionVersionClassMethodTest(CollectionBaseTest):

    def setUp(self):
        super(CollectionVersionClassMethodTest, self).setUp()
        self.collection1 = Collection.objects.create(
            name='collection1',
            mnemonic='collection1',
            owner=self.user1,
            parent=self.org1,
            full_name='Collection One',
            collection_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection'
        )
        self.collection2 = Collection.objects.create(
            name='collection2',
            mnemonic='collection2',
            owner=self.user1,
            parent=self.userprofile1,
            full_name='Collection Two',
            collection_type=DICTIONARY_SRC_TYPE,
            public_access=EDIT_ACCESS_TYPE,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.collection2.com',
            description='This is the second test collection'
        )

    def test_for_base_object_positive(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.full_clean()
        version1.save()
        self.assertEquals(version1.mnemonic, 'version1')
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(self.collection1.name, version1.name)
        self.assertEquals(self.collection1.full_name, version1.full_name)
        self.assertEquals(self.collection1.collection_type, version1.collection_type)
        self.assertEquals(self.collection1.public_access, version1.public_access)
        self.assertEquals(self.collection1.default_locale, version1.default_locale)
        self.assertEquals(self.collection1.supported_locales, version1.supported_locales)
        self.assertEquals(self.collection1.website, version1.website)
        self.assertEquals(self.collection1.description, version1.description)
        self.assertFalse(version1.released)
        self.assertIsNone(version1.parent_version)
        self.assertIsNone(version1.previous_version)
        self.assertEquals(1, self.collection1.num_versions)

    def test_for_base_object_negative__no_collection(self):
        with self.assertRaises(ValidationError):
            version1 = CollectionVersion.for_base_object(None, 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__illegal_collection(self):
        with self.assertRaises(ValidationError):
            version1 = CollectionVersion.for_base_object(self.org1, 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__newborn_collection(self):
        with self.assertRaises(ValidationError):
            version1 = CollectionVersion.for_base_object(Collection(), 'version1')
            version1.full_clean()
            version1.save()

    def test_for_base_object_negative__bad_previous_version(self):
        with self.assertRaises(ValueError):
            version1 = CollectionVersion.for_base_object(self.collection1, 'version1', previous_version=self.collection1)
            version1.full_clean()
            version1.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_for_base_object_negative__bad_parent_version(self):
        with self.assertRaises(ValueError):
            version1 = CollectionVersion.for_base_object(self.collection1, 'version1', parent_version=self.collection1)
            version1.full_clean()
            version1.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_persist_changes_positive(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description

        id = version1.id
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(0, len(errors))

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertNotEquals(mnemonic, version1.mnemonic)
        self.assertNotEquals(released, version1.released)
        self.assertNotEquals(description, version1.description)

    def test_persist_changes_negative__bad_previous_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description

        id = version1.id
        version1._previous_version_mnemonic = 'No such version'
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('previousVersion' in errors)

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)

    def test_persist_changes_negative__previous_version_is_self(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description

        id = version1.id
        version1._previous_version_mnemonic = mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('previousVersion' in errors)

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)

    def test_persist_changes_negative__bad_parent_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description

        id = version1.id
        version1._parent_version_mnemonic = 'No such version'
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('parentVersion' in errors)

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)

    def test_persist_changes_negative__parent_version_is_self(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
        version1.full_clean()
        version1.save()

        mnemonic = version1.mnemonic
        released = version1.released
        description = version1.description

        id = version1.id
        version1._parent_version_mnemonic = mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(1, len(errors))
        self.assertTrue('parentVersion' in errors)

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(mnemonic, version1.mnemonic)
        self.assertEquals(released, version1.released)
        self.assertEquals(description, version1.description)

    def test_persist_changes_positive__good_previous_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description

        id = version2.id
        version2._previous_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.previous_version)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)

    def test_persist_changes_positive__good_parent_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.parent_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description

        id = version2.id
        version2._parent_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.parent_version)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)

    def test_persist_changes_positive__seed_from_previous(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.concept_references = [1]
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description

        id = version2.id
        version2._previous_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals([], version2.concept_references)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)

        errors = CollectionVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.previous_version)
        self.assertEquals([1], version2.concept_references)

    def test_persist_changes_positive__seed_from_parent(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.concept_references = [2]
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.parent_version)

        mnemonic = version2.mnemonic
        released = version2.released
        description = version2.description

        id = version2.id
        version2._parent_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version2)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals([], version2.concept_references)
        self.assertNotEquals(mnemonic, version2.mnemonic)
        self.assertNotEquals(released, version2.released)
        self.assertNotEquals(description, version2.description)

        errors = CollectionVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.parent_version)
        self.assertEquals([2], version2.concept_references)

    def test_persist_changes_positive__seed_from_previous_over_parent(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.concept_references = [1]
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.concept_references = [2]
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        version3 = CollectionVersion.for_base_object(self.collection1, 'version3')
        version3.full_clean()
        version3.save()

        mnemonic = version3.mnemonic
        released = version3.released
        description = version3.description

        id = version3.id
        version3._parent_version_mnemonic = 'version2'
        version3._previous_version_mnemonic = 'version1'
        version3.mnemonic = "%s-prime" % mnemonic
        version3.released = not released
        version3.description = "%s-prime" % description

        errors = CollectionVersion.persist_changes(version3)
        self.assertEquals(0, len(errors))

        version3 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version3.versioned_object)
        self.assertEquals(3, self.collection1.num_versions)
        self.assertEquals(version3, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version3.previous_version)
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals([], version3.concept_references)
        self.assertNotEquals(mnemonic, version3.mnemonic)
        self.assertNotEquals(released, version3.released)
        self.assertNotEquals(description, version3.description)

        errors = CollectionVersion.persist_changes(version3, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version3 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version3.versioned_object)
        self.assertEquals(3, self.collection1.num_versions)
        self.assertEquals(version3, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals(version1, version3.previous_version)
        self.assertEquals([1], version3.concept_references)

