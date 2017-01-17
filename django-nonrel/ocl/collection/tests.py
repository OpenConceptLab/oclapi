"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from collection.models import CollectionReference
from collection.validation_messages import REFERENCE_ALREADY_EXISTS, CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE, \
    CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE
from oclapi.models import ACCESS_TYPE_VIEW, CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import *


class CollectionBaseTest(OclApiBaseTestCase):
    def setUp(self):
        super(CollectionBaseTest, self).setUp()
        self.user1 = User.objects.create(
            username='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User',
            password='user1'
        )
        self.user2 = User.objects.create(
            username='user2',
            email='user2@test.com',
            last_name='Two',
            first_name='User',
            password='user2'
        )

        self.userprofile1 = UserProfile.objects.create(user=self.user1, mnemonic='user1')
        self.userprofile2 = UserProfile.objects.create(user=self.user2, mnemonic='user2')

        self.org1 = Organization.objects.create(name='org1', mnemonic='org1')
        self.org2 = Organization.objects.create(name='org2', mnemonic='org2')
        self.name = create_localized_text(name='Fred', locale='es', type='FULLY_SPECIFIED')


class CollectionTest(CollectionBaseTest):
    def test_create_collection_positive(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                updated_by=self.user1)
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
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1,
                                parent=self.userprofile1,
                                collection_type='Dictionary', public_access=ACCESS_TYPE_EDIT, updated_by=self.user1)
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
            collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1,
                                    parent=self.userprofile1,
                                    collection_type='Dictionary', public_access='INVALID', updated_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_positive__valid_attributes(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1,
                                parent=self.userprofile1,
                                collection_type='Dictionary', public_access=ACCESS_TYPE_EDIT, updated_by=self.user1)
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
            collection = Collection(mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                    updated_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', created_by=self.user1, parent=self.org1, updated_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_created_by(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', parent=self.org1, updated_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_updated_by(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', parent=self.org1, created_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1,
                                    updated_by=self.user1)
            collection.full_clean()
            collection.save()

    def test_create_collection_negative__mnemonic_exists(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                updated_by=self.user1)
        collection.full_clean()
        collection.save()
        self.assertEquals(0, collection.num_versions)
        with self.assertRaises(ValidationError):
            collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user2, parent=self.org1,
                                    updated_by=self.user2)
            collection.full_clean()
            collection.save()

    def test_create_positive__mnemonic_exists(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                updated_by=self.user1)
        collection.full_clean()
        collection.save()
        self.assertEquals(1, Collection.objects.filter(
            mnemonic='collection1',
            parent_type=ContentType.objects.get_for_model(Organization),
            parent_id=self.org1.id
        ).count())
        self.assertEquals(0, collection.num_versions)

        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1,
                                parent=self.userprofile1, updated_by=self.user1)
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

    def test_add_concept_reference(self):
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

        (concept1, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        reference = '/orgs/org1/sources/source/concepts/' + concept1.mnemonic + '/'
        collection.expressions = [reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.mappings), 0)
        self.assertEquals(len(head.concepts), 1)
        self.assertEquals(len(head.references), 1)

    def test_delete_single_mapping_reference(self):
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

        (fromConcept, errors) = create_concept(mnemonic="fromConcept", user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        (toConcept, errors) = create_concept(mnemonic="toConcept", user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        mapping = Mapping(
            map_type='Same As',
            from_concept=fromConcept,
            to_concept=toConcept,
            external_id='mapping',
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)

        reference = '/orgs/org1/sources/source/mappings/' + Mapping.objects.filter()[0].id + '/'
        collection.expressions = [reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.mappings), 1)
        self.assertEquals(len(head.references), 1)

        reference += mapping.get_latest_version.mnemonic + '/'

        collection.delete_references([reference])

        head = CollectionVersion.get_head(collection.id)
        collection = Collection.objects.get(id=collection.id)

        self.assertEquals(len(collection.references), 0)
        self.assertEquals(len(head.references), 0)
        self.assertEquals(len(head.mappings), 0)

    def test_delete_concept_reference(self):
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

        (concept1, error) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=source,
            names=[create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')],
        )

        expression = '/orgs/org1/sources/source/concepts/' + concept1.mnemonic + '/'
        collection.expressions = [expression]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.concepts), 1)
        self.assertEquals(len(head.references), 1)
        expression += concept1.get_latest_version.id + '/'
        collection.delete_references([expression])

        head = CollectionVersion.get_head(collection.id)
        collection = Collection.objects.get(id=collection.id)

        self.assertEquals(len(collection.references), 0)
        self.assertEquals(len(head.references), 0)
        self.assertEquals(len(head.concepts), 0)

    def test_delete_multiple_reference(self):
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

        (concept1, errors) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=source,
            names=[create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')],
        )

        (from_concept, error) = create_concept(
            mnemonic='fromConcept',
            user=self.user1,
            source=source,
            names=[create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')],
        )

        (to_concept, error) = create_concept(
            mnemonic='toConcept',
            user=self.user1,
            source=source,
            names=[create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')],
        )

        mapping = Mapping(
            map_type='Same As',
            from_concept=from_concept,
            to_concept=to_concept,
            external_id='mapping',
        )
        kwargs = {
            'parent_resource': source,
        }

        Mapping.persist_new(mapping, self.user1, **kwargs)

        from_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=from_concept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=concept1.mnemonic).mnemonic + '/'
        mapping_reference = '/orgs/org1/sources/source/mappings/' + Mapping.objects.filter()[0].id + '/'

        references = [concept1_reference, from_concept_reference, mapping_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.concepts), 2)
        self.assertEquals(len(head.mappings), 1)
        self.assertEquals(len(head.references), 3)

        references[0] += '{}/'.format(concept1.get_latest_version.id)
        references[2] += '{}/'.format(Mapping.objects.filter()[0].get_latest_version.mnemonic)

        deleted_concepts, deleted_mappings = collection.delete_references([references[0], references[2]])

        head = CollectionVersion.get_head(collection.id)
        collection = Collection.objects.get(id=collection.id)

        self.assertEquals(len(deleted_concepts), 1)
        self.assertEquals(len(deleted_mappings), 1)
        self.assertEquals(len(collection.references), 1)
        from_concept_reference_with_version_id = '{}{}/'.format(from_concept_reference,
                                                                from_concept.get_latest_version.id)
        self.assertEquals(collection.references[0].expression, from_concept_reference_with_version_id)
        self.assertEquals(len(head.references), 1)
        self.assertEquals(len(head.concepts), 1)
        self.assertEquals(len(head.mappings), 0)
        self.assertEquals(head.references[0].expression, from_concept_reference_with_version_id)
        self.assertEquals(head.concepts[0], from_concept.get_latest_version.id)

    def test_delete_reference_when_no_reference_given(self):
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

        self.assertEquals(collection.delete_references([]), [[], []])

    def test_concepts_url(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                updated_by=self.user1)
        collection.full_clean()
        collection.save()

        self.assertEquals(collection.concepts_url, '/orgs/org1/sources/collection1/concepts/')

    def test_mappings_url(self):
        collection = Collection(name='collection1', mnemonic='collection1', created_by=self.user1, parent=self.org1,
                                updated_by=self.user1)
        collection.full_clean()
        collection.save()

        self.assertEquals(collection.mappings_url, '/orgs/org1/sources/org1/concepts/collection1/mappings/')

    def test_create_collection_with_openmrs_validation(self):
        user = create_user()
        org = create_organization()

        collection = Collection(
            name='collection1',
            mnemonic='collection1',
            created_by=user,
            parent=org,
            updated_by=user,
            custom_validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS
        )

        collection.full_clean()
        collection.save()
        self.assertEquals("OpenMRS", collection.custom_validation_schema)


class CollectionClassMethodTest(CollectionBaseTest):
    def setUp(self):
        super(CollectionClassMethodTest, self).setUp()
        self.new_collection = Collection(
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

    def test_persist_new_positive(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Collection.objects.filter(name='collection1').exists())
        collection = Collection.objects.get(name='collection1')
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=collection.id))
        collection_version = CollectionVersion.objects.get(versioned_object_id=collection.id)
        self.assertEquals(1, collection.num_versions)
        self.assertEquals(collection_version, CollectionVersion.get_latest_version_of(collection))

    def test_delete_collection_allversion_also_deleted(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Collection.objects.filter(name='collection1').exists())
        id = Collection.objects.get(name='collection1').id
        self.assertTrue(CollectionVersion.objects.filter(versioned_object_id=id))
        Collection.objects.get(name='collection1').delete()
        self.assertFalse(Collection.objects.filter(name='collection1').exists())
        self.assertFalse(CollectionVersion.objects.filter(versioned_object_id=id))

    def test_persist_new_negative__no_parent(self):
        errors = Collection.persist_new(self.new_collection, self.user1)
        self.assertTrue('parent' in errors)
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_new_negative__no_owner(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, None, **kwargs)
        self.assertTrue('created_by' in errors)
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_new_negative__no_name(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        self.new_collection.name = None
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
        self.assertTrue('name' in errors)
        self.assertFalse(Collection.objects.filter(name='collection1').exists())

    def test_persist_changes_positive(self):
        kwargs = {
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
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
        self.new_collection.collection_type = 'Reference'
        self.new_collection.public_access = ACCESS_TYPE_VIEW
        self.new_collection.default_locale = "%s_prime" % default_locale
        self.new_collection.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_collection.website = "%s_prime" % website
        self.new_collection.description = "%s_prime" % description

        errors = Collection.persist_changes(self.new_collection, self.user1, **kwargs)
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
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
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

        errors = Collection.persist_changes(self.new_collection, self.user1, **kwargs)
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
            'parent_resource': self.userprofile1
        }
        errors = Collection.persist_new(self.new_collection, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

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
        errors = Collection.persist_new(collection, self.user1, **kwargs)
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
        self.new_collection.collection_type = 'Reference'
        self.new_collection.public_access = ACCESS_TYPE_VIEW
        self.new_collection.default_locale = "%s_prime" % default_locale
        self.new_collection.supported_locales = ["%s_prime" % supported_locales[0]]
        self.new_collection.website = "%s_prime" % website
        self.new_collection.description = "%s_prime" % description

        errors = Collection.persist_changes(self.new_collection, self.user1, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)
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

    def test_add_invalid_expression_to_collection_negative(self):
        expression = '/foobar'
        errors = Collection.persist_changes(self.new_collection, 'foobar', expressions=[expression])
        self.assertEquals(errors.get('references')[0][expression][0], 'Expression specified is not valid.')


class CollectionVersionTest(CollectionBaseTest):
    def setUp(self):
        super(CollectionVersionTest, self).setUp()
        self.collection1 = Collection.objects.create(name='collection1', mnemonic='collection1', created_by=self.user1,
                                                     updated_by=self.user1, parent=self.org1, external_id='EXTID1')
        self.collection2 = Collection.objects.create(name='collection2', mnemonic='collection2', created_by=self.user1,
                                                     updated_by=self.user1, parent=self.userprofile1)

    def test_collection_version_create_positive(self):
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
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
                versioned_object=self.collection1,
                created_by=self.user1,
                updated_by=self.user1,
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                name='version1',
                versioned_object=self.collection1,
                created_by=self.user1,
                updated_by=self.user1,
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__no_collection(self):
        with self.assertRaises(ValidationError):
            collection_version = CollectionVersion(
                mnemonic='version1',
                name='version1',
                created_by=self.user1,
                updated_by=self.user1,
            )
            collection_version.full_clean()
            collection_version.save()
        self.assertEquals(0, self.collection1.num_versions)

    def test_collection_version_create_negative__same_mnemonic(self):
        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=self.collection1,
            created_by=self.user1,
            updated_by=self.user1,
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
            versioned_object=self.collection1,
            created_by=self.user1,
            updated_by=self.user1,

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
            versioned_object=self.collection2,
            created_by=self.user1,
            updated_by=self.user1,
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
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
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
            previous_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
            previous_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
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
            parent_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
            parent_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
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
            parent_version=version1,
            created_by=self.user1,
            updated_by=self.user1,
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
            previous_version=version2,
            created_by=self.user1,
            updated_by=self.user1,
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

    def test_export_path(self):
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
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection not Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection.com',
            description='This is the not second test collection'
        )
        kwargs = {
            'parent_resource': self.userprofile1
        }
        Collection.persist_new(collection, self.user1, **kwargs)
        collection = Collection.objects.get(mnemonic=collection.mnemonic)
        Source.persist_new(source, self.user1, parent_resource=self.org1)

        (concept, _) = create_concept(mnemonic="concept", user=self.user1, source=source)

        collection.expression = '/orgs/org1/sources/source/concepts/concept/'
        collection.full_clean()
        collection.save()

        version = CollectionVersion.for_base_object(collection, 'version1')
        kwargs = {}
        CollectionVersion.persist_new(version, **kwargs)

        collection_version = CollectionVersion.get_latest_version_of(collection)
        self.assertEquals(collection_version.export_path,
                          "user1/collection_version1." + collection_version.last_child_update.strftime(
                              '%Y%m%d%H%M%S') + ".tgz")

    def test_last_child_update(self):
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
        collection = Collection(
            name='collection',
            mnemonic='collection',
            full_name='Collection not Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection.com',
            description='This is the not second test collection'
        )
        kwargs = {
            'parent_resource': self.userprofile1
        }
        Collection.persist_new(collection, self.user1, **kwargs)
        collection = Collection.objects.get(mnemonic=collection.mnemonic)
        Source.persist_new(source, self.user1, parent_resource=self.org1)

        (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)

        collection.expressions = ['/orgs/org1/sources/source/concepts/concept/']
        collection.full_clean()
        collection.save()

        version = CollectionVersion.for_base_object(collection, 'version1')
        kwargs = {}
        CollectionVersion.persist_new(version, **kwargs)

        collection_version = CollectionVersion.get_latest_version_of(collection)
        concept = Concept.objects.get(mnemonic=concept.mnemonic)
        concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id)
        self.assertEquals(collection_version.last_child_update, concept_version.updated_at)

    def test_last_child_update_without_child(self):
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
        collection_version = CollectionVersion.get_latest_version_of(collection)
        self.assertEquals(collection_version.last_child_update, collection_version.updated_at)

    def test_seed_concepts(self):
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

        (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)

        (concept2, errors) = create_concept(mnemonic="concept2", user=self.user1, source=source)

        concept1_version = ConceptVersion.objects.get(versioned_object_id=concept.id)
        concept2_latest_version = concept2.get_latest_version

        head_version = CollectionVersion(
            name='HEAD',
            mnemonic='HEAD',
            versioned_object=self.collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
            concepts=[concept2.id, concept1_version.id]
        )
        head_version.full_clean()
        head_version.save()

        version1 = CollectionVersion(
            name='v1',
            mnemonic='v1',
            versioned_object=self.collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        version1.full_clean()
        version1.save()

        self.assertEquals(len(version1.concepts), 0)
        version1.seed_concepts()
        self.assertEquals(len(version1.concepts), 2)
        self.assertEquals(version1.concepts, [concept2_latest_version.id, concept1_version.id])

    def test_seed_mappings(self):
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

        (from_concept1, errors) = create_concept(mnemonic="fromConcept1", user=self.user1, source=source)

        (from_concept2, errors) = create_concept(mnemonic="fromConcept2", user=self.user1, source=source)

        (to_concept, errors) = create_concept(mnemonic="toConcept", user=self.user1, source=source)

        mapping = Mapping(
            map_type='Same As',
            from_concept=from_concept1,
            to_concept=to_concept,
            external_id='mapping',
            retired=True,
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)

        mapping2 = Mapping(
            map_type='Same As',
            from_concept=from_concept2,
            to_concept=to_concept,
            external_id='mapping',
            retired=True,
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping2, self.user1, **kwargs)
        mapping2_version = MappingVersion.objects.get(versioned_object_id=mapping2.id)
        mapping1_latest_version = mapping.get_latest_version

        head_version = CollectionVersion(
            name='HEAD',
            mnemonic='HEAD',
            versioned_object=self.collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
            mappings=[mapping2_version.id, mapping.id]
        )
        head_version.full_clean()
        head_version.save()

        version1 = CollectionVersion(
            name='v1',
            mnemonic='v1',
            versioned_object=self.collection1,
            released=True,
            created_by=self.user1,
            updated_by=self.user1,
        )
        version1.full_clean()
        version1.save()

        self.assertEquals(len(version1.mappings), 0)
        version1.seed_mappings()
        self.assertEquals(len(version1.mappings), 2)
        self.assertEquals(version1.mappings, [mapping2_version.id, mapping1_latest_version.id])


class CollectionVersionClassMethodTest(CollectionBaseTest):
    def setUp(self):
        super(CollectionVersionClassMethodTest, self).setUp()
        self.collection1 = Collection.objects.create(
            name='collection1',
            mnemonic='collection1',
            parent=self.org1,
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection',
            created_by=self.user1,
            updated_by=self.user1,
            external_id='EXTID1',
        )

        self.collection2 = Collection.objects.create(
            name='collection2',
            mnemonic='collection2',
            parent=self.userprofile1,
            full_name='Collection Two',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='fr',
            supported_locales=['fr'],
            website='www.collection2.com',
            description='This is the second test collection',
            created_by=self.user1,
            updated_by=self.user1,
            external_id='EXTID2',
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
        self.assertEquals(self.collection1.external_id, version1.external_id)
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
            version1 = CollectionVersion.for_base_object(self.collection1, 'version1',
                                                         previous_version=self.collection1)
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
        external_id = version1.external_id

        id = version1.id
        version1.mnemonic = "%s-prime" % mnemonic
        version1.released = not released
        version1.description = "%s-prime" % description
        version1.external_id = "%s-prime" % external_id

        errors = CollectionVersion.persist_changes(version1)
        self.assertEquals(0, len(errors))

        version1 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version1.versioned_object)
        self.assertEquals(1, self.collection1.num_versions)
        self.assertEquals(version1, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertNotEquals(mnemonic, version1.mnemonic)
        self.assertNotEquals(released, version1.released)
        self.assertNotEquals(description, version1.description)
        self.assertNotEquals(external_id, version1.external_id)

    # @skip('Tests dont exist anymore: New version will seed data from HEAD always, and never from previous version')
    def test_persist_changes_negative__bad_previous_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
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
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__previous_version_is_self(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
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
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__bad_parent_version(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
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
        self.assertEquals(external_id, version1.external_id)

    def test_persist_changes_negative__parent_version_is_self(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1', released=True)
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
        self.assertEquals(external_id, version1.external_id)

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
        external_id = version2.external_id

        id = version2.id
        version2._previous_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

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
        self.assertNotEquals(external_id, version2.external_id)

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
        external_id = version2.external_id

        id = version2.id
        version2._parent_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

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
        self.assertNotEquals(external_id, version2.external_id)

    @skip('Tests dont exist anymore: New version will seed data from HEAD always, and never from previous version')
    def test_persist_changes_positive__seed_from_previous(self):
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
        external_id = version2.external_id

        id = version2.id
        version2._previous_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

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
        self.assertNotEquals(external_id, version2.external_id)

        errors = CollectionVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.previous_version)

    @skip('Tests dont exist anymore: New version will seed data from HEAD always, and never from previous version')
    def test_persist_changes_positive__seed_from_parent(self):
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
        external_id = version2.external_id

        id = version2.id
        version2._parent_version_mnemonic = 'version1'
        version2.mnemonic = "%s-prime" % mnemonic
        version2.released = not released
        version2.description = "%s-prime" % description
        version2.external_id = "%s-prime" % external_id

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
        self.assertNotEquals(external_id, version2.external_id)

        errors = CollectionVersion.persist_changes(version2, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version2 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version2.versioned_object)
        self.assertEquals(2, self.collection1.num_versions)
        self.assertEquals(version2, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version2.parent_version)

    @skip('Tests dont exist anymore: New version will seed data from HEAD always, and never from previous version')
    def test_persist_changes_positive__seed_from_previous_over_parent(self):
        version1 = CollectionVersion.for_base_object(self.collection1, 'version1')
        version1.full_clean()
        version1.save()

        version2 = CollectionVersion.for_base_object(self.collection1, 'version2')
        version2.full_clean()
        version2.save()
        self.assertIsNone(version2.previous_version)

        version3 = CollectionVersion.for_base_object(self.collection1, 'version3')
        version3.full_clean()
        version3.save()

        mnemonic = version3.mnemonic
        released = version3.released
        description = version3.description
        external_id = version3.external_id

        id = version3.id
        version3._parent_version_mnemonic = 'version2'
        version3._previous_version_mnemonic = 'version1'
        version3.mnemonic = "%s-prime" % mnemonic
        version3.released = not released
        version3.description = "%s-prime" % description
        version3.external_id = "%s-prime" % external_id

        errors = CollectionVersion.persist_changes(version3)
        self.assertEquals(0, len(errors))

        version3 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version3.versioned_object)
        self.assertEquals(3, self.collection1.num_versions)
        self.assertEquals(version3, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version1, version3.previous_version)
        self.assertEquals(version2, version3.parent_version)
        self.assertNotEquals(mnemonic, version3.mnemonic)
        self.assertNotEquals(released, version3.released)
        self.assertNotEquals(description, version3.description)
        self.assertNotEquals(external_id, version3.external_id)

        errors = CollectionVersion.persist_changes(version3, seed_concepts=True)
        self.assertEquals(0, len(errors))

        version3 = CollectionVersion.objects.get(id=id)
        self.assertEquals(self.collection1, version3.versioned_object)
        self.assertEquals(3, self.collection1.num_versions)
        self.assertEquals(version3, CollectionVersion.get_latest_version_of(self.collection1))
        self.assertEquals(version2, version3.parent_version)
        self.assertEquals(version1, version3.previous_version)

        def test_collection_active_concepts_and_mappings(self):
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

            (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)
            (concept1, errors) = create_concept(mnemonic="concept1", user=self.user1, source=source)

            self.collection1.expressions = [
                '/orgs/org1/sources/source/concepts/concept/',
                '/orgs/org1/sources/source/concepts/concept1/'
            ]
            self.collection1.full_clean()
            self.collection1.save()

            collection_version = CollectionVersion(
                name='version1',
                mnemonic='version1',
                versioned_object=self.collection1,
                created_by=self.user1,
                updated_by=self.user1,
            )
            collection_version.full_clean()
            collection_version.save()

            self.assertEquals(len(collection_version.concepts), 1)
            self.assertEquals(len(collection_version.references), 1)
            self.assertEquals(collection_version.active_concepts, 1)


class CollectionReferenceTest(CollectionBaseTest):
    def setUp(self):
        super(CollectionReferenceTest, self).setUp()
        self.collection1 = Collection.objects.create(
            name='collection1',
            mnemonic='collection1',
            parent=self.org1,
            full_name='Collection One',
            collection_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.collection1.com',
            description='This is the first test collection',
            created_by=self.user1,
            updated_by=self.user1,
            external_id='EXTID1',
        )

    def test_add_invalid_expression_to_collection_negative(self):
        reference = CollectionReference(expression='')
        try:
            reference.full_clean()
            self.assertTrue(False)
        except ValidationError as e:
            self.assertEquals(len(e.messages), 2)
            self.assertEquals(e.messages, ['This field cannot be blank.', 'Expression specified is not valid.'])

    def test_reference_type_of_expression(self):
        reference = CollectionReference(
            expression='/users/gaurav/sources/ABC-10/concepts/a15/'
        )
        self.assertEquals(reference.reference_type, 'concepts')

    def test_reference_as_concept_version(self):
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

        (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)

        concept_version = ConceptVersion.objects.get(versioned_object_id=concept.id)

        expression = '/orgs/' + self.org1.mnemonic + '/sources/' + \
                     source.mnemonic + '/concepts/' + concept.mnemonic + '/' + concept_version.id + '/'

        reference = CollectionReference(expression=expression)
        reference.full_clean()

        self.assertEquals(len(reference.concepts), 1)
        self.assertEquals(type(reference.concepts[0]), ConceptVersion)
        self.assertEquals(reference.concepts[0].id, concept_version.id)

    def test_reference_as_mapping_version(self):
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

        (from_concept, errors) = create_concept(mnemonic="fromConcept", user=self.user1, source=source)
        (to_concept, errors) = create_concept(mnemonic="toConcept", user=self.user1, source=source)

        mapping = Mapping(
            map_type='Same As',
            from_concept=from_concept,
            to_concept=to_concept,
            external_id='mapping',
            retired=True,
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        mapping_version = MappingVersion.objects.get(versioned_object_id=mapping.id)

        reference = CollectionReference(expression='/orgs/org1/sources/source/mappings/' + Mapping.objects.filter()[
            0].id + '/' + mapping_version.mnemonic + '/')

        reference.full_clean()

        self.assertEquals(len(reference.mappings), 1)
        self.assertEquals(type(reference.mappings[0]), MappingVersion)
        self.assertEquals(reference.mappings[0].id, mapping_version.id)

    def test_adding_retired_concept_negative(self):
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

        (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)

        expression = '/orgs/' + self.org1.mnemonic + '/sources/' + \
                     source.mnemonic + '/concepts/' + concept.mnemonic + '/'

        reference = CollectionReference(expression=expression)
        try:
            reference.full_clean()
        except ValidationError as e:
            self.assertTrue(False)

    def test_adding_retired_mapping_positive(self):
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

        (from_concept, errors) = create_concept(mnemonic="fromConcept", user=self.user1, source=source)
        (to_concept, errors) = create_concept(mnemonic="toConcept", user=self.user1, source=source)

        mapping = Mapping(
            map_type='Same As',
            from_concept=from_concept,
            to_concept=to_concept,
            external_id='mapping',
            retired=True,
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)

        reference = CollectionReference(
            expression='/orgs/org1/sources/source/mappings/' + Mapping.objects.filter()[0].id + '/')
        try:
            reference.full_clean()
        except ValidationError as e:
            self.assertTrue(False)

    def test_add_concept_as_single_reference_without_version_information_should_add_latest_version_number(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        concept_version_number = concept.get_latest_version.id

        single_reference = '/users/{}/sources/{}/concepts/{}/'.format(self.user1.username, source.name,
                                                                      concept.mnemonic)
        collection.expressions = [single_reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.concepts), 1)
        self.assertEquals(len(errors), 0)
        self.assertEquals(collection.current_references()[0], single_reference + concept_version_number + '/')
        self.assertEquals(head.concepts[0], concept_version_number)

    def test_add_concept_as_multiple_reference_without_version_information_should_add_latest_versions_numbers(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        (concept_two, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='FULLY_SPECIFIED')])

        concept_one_reference = '/users/{}/sources/{}/concepts/{}/'.format(self.user1.username, source.name,
                                                                           concept_one.mnemonic)
        concept_two_reference = '/users/{}/sources/{}/concepts/{}/'.format(self.user1.username, source.name,
                                                                           concept_two.mnemonic)

        collection.expressions = [concept_one_reference, concept_two_reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.concepts), 2)
        self.assertEquals(len(errors), 0)
        self.assertEquals(collection.current_references()[0],
                          concept_one_reference + concept_one.get_latest_version.id + '/')
        self.assertEquals(collection.current_references()[1],
                          concept_two_reference + concept_two.get_latest_version.id + '/')

    def test_add_mapping_as_single_reference_without_version_information_should_add_latest_version_number(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        (concept_two, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='FULLY_SPECIFIED')])

        mapping = create_mapping(self.user1, source, concept_one, concept_two, "Broader Than")

        mapping_version_number = mapping.get_latest_version.mnemonic + '/'

        single_reference = '/users/{}/sources/{}/mappings/{}/'.format(self.user1.username, source.name,
                                                                      mapping.mnemonic)
        collection.expressions = [single_reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        self.assertEquals(len(head.mappings), 1)
        self.assertEquals(collection.current_references()[0], single_reference + mapping_version_number)

    def test_add_mapping_as_multiple_reference_without_version_information_should_add_latest_versions_numbers(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        (concept_two, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='FULLY_SPECIFIED')])

        mapping_one = create_mapping(self.user1, source, concept_one, concept_two, "BROADER-THAN")
        mapping_two = create_mapping(self.user1, source, concept_two, concept_one, "SAME-AS")

        mapping_one_reference = '/users/{}/sources/{}/mappings/{}/'.format(self.user1.username, source.name,
                                                                           mapping_one.mnemonic)

        mapping_two_reference = '/users/{}/sources/{}/mappings/{}/'.format(self.user1.username, source.name,
                                                                           mapping_two.mnemonic)
        collection.expressions = [mapping_one_reference, mapping_two_reference]
        collection.full_clean()
        collection.save()

        head = CollectionVersion.get_head(collection.id)

        mapping_one_version_number = mapping_one.get_latest_version.mnemonic + '/'
        mapping_two_version_number = mapping_two.get_latest_version.mnemonic + '/'

        self.assertEquals(len(head.mappings), 2)
        self.assertEquals(collection.current_references()[0], mapping_one_reference + mapping_one_version_number)
        self.assertEquals(collection.current_references()[0], mapping_one_reference + mapping_two_version_number)

    def test_add_duplicate_concept_reference_should_not_add(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='None')])

        collection.expressions = [concept_one.url]
        collection.full_clean()
        collection.save()

        with self.assertRaisesRegexp(ValidationError, REFERENCE_ALREADY_EXISTS):
            collection.expressions = [concept_one.url]
            collection.full_clean()
            collection.save()

        self.assertEquals(len(collection.current_references()), 1)

    def test_add_duplicate_concept_reference_different_version_number(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        source = create_source(self.user1)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='None')])

        collection.expressions = [concept_one.url]
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=concept_one,
            concept_class='Diagnosis',
            datatype=concept_one.datatype,
            names=concept_one.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")]
        )

        concept_version.full_clean()
        concept_version.save()

        with self.assertRaisesRegexp(ValidationError, REFERENCE_ALREADY_EXISTS):
            collection.expressions = [concept_version.url]
            collection.full_clean()
            collection.save()

        self.assertEquals(len(collection.current_references()), 1)

    def test_add_duplicate_concept_reference_different_version_number(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        source = create_source(self.user1)

        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='None')])

        collection.expressions = [concept_one.url]
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=concept_one,
            concept_class='Diagnosis',
            datatype=concept_one.datatype,
            names=concept_one.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")]
        )

        concept_version.full_clean()
        concept_version.save()

        with self.assertRaisesRegexp(ValidationError, REFERENCE_ALREADY_EXISTS):
            collection.expressions = [concept_version.url]
            collection.full_clean()
            collection.save()

        self.assertEquals(len(collection.current_references()), 1)

    def test_add_duplicate_mapping_reference_different_version_number(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        source = create_source(self.user1)
        (concept_one, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='None')])

        (concept_two, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='en', type='FULLY_SPECIFIED')])

        mapping = create_mapping(self.user1, source, concept_one, concept_two, "SAME-AS")

        collection.expressions = [mapping.url]
        collection.full_clean()
        collection.save()

        mapping_version = MappingVersion(
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            from_concept=concept_one,
            to_concept=concept_two,
            external_id='mapping1',
            versioned_object_id=mapping.id,
            versioned_object_type=ContentType.objects.get_for_model(Mapping),
            mnemonic='1'
        )

        with self.assertRaisesRegexp(ValidationError, REFERENCE_ALREADY_EXISTS):
            collection.expressions = [mapping_version.url]
            collection.full_clean()
            collection.save()

        self.assertEquals(len(collection.current_references()), 1)

    def test_add_duplicate_mapping_reference_should_not_add(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (from_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])
        (to_concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='User', locale='es', type='FULLY_SPECIFIED')])

        mapping = create_mapping(self.user1, source, from_concept, to_concept)

        collection.expressions = [mapping.url, from_concept.url]
        collection.full_clean()
        collection.save()

        kwargs = {
            'parent_resource': self.user1,
            'expressions': [mapping.url]
        }
        errors = Collection.persist_changes(collection, self.user1, **kwargs)

        self.assertEquals(len(errors), 1)
        self.assertIn(REFERENCE_ALREADY_EXISTS, errors['references'][0][mapping.url])
        self.assertEquals(len(collection.current_references()), 2)

    def test_concept_fully_specified_name_within_collection_should_be_unique(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source1 = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        source2 = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, _) = create_concept(user=self.user1, source=source1, names=[
            create_localized_text(name='Non Unique Name', locale='en', type='FULLY_SPECIFIED')])

        collection.expressions = [concept_one.url]
        collection.full_clean()
        collection.save()

        (concept_two, errors) = create_concept(user=self.user1, source=source2, names=[
            create_localized_text(name='Non Unique Name', locale='en', type='FULLY_SPECIFIED')])

        kwargs = {
            'parent_resource': self.user1,
            'expressions': [concept_two.url]
        }

        errors = Collection.persist_changes(collection, self.user1, **kwargs)

        self.assertEquals(len(errors), 1)
        actual_message = errors['references'][0][concept_two.url]
        self.assertIn(CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE, actual_message)

    def test_preferred_name_within_collection_should_be_unique(self):
        collection = create_collection(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        source1 = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        source2 = create_source(self.user1, CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept_one, errors) = create_concept(user=self.user1, source=source1, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name', locale='en', type='Fully Specified')
        ])

        collection.expressions = [concept_one.url]
        collection.full_clean()
        collection.save()

        (concept_two, errors) = create_concept(user=self.user1, source=source2, names=[
            create_localized_text(name='Non Unique Name', locale_preferred=True, locale='en', type='None'),
            create_localized_text(name='Any Name 2', locale='en', type='Fully Specified')
        ])

        kwargs = {
            'parent_resource': self.user1,
            'expressions': [concept_two.url]
        }

        errors = Collection.persist_changes(collection, self.user1, **kwargs)

        self.assertEquals(len(errors), 1)
        actual_message = errors['references'][0][concept_two.url]
        self.assertIn(CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE, actual_message)

    def test_diff(self):
        superset = [CollectionReference(expression='foo'), CollectionReference(expression='bar')]
        subset = [CollectionReference(expression='foo'), CollectionReference(expression='tao')]
        self.assertEquals(CollectionReference.diff(superset, subset), [superset[1]])
        self.assertEquals(CollectionReference.diff(subset, superset), [subset[1]])


class CollectionVersionReferenceTest(CollectionReferenceTest):
    def test_add_valid_concept_expression_to_collection_positive(self):
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

        (concept, errors) = create_concept(mnemonic="concept", user=self.user1, source=source)

        version = CollectionVersion.for_base_object(self.collection1, 'version1')
        reference = CollectionReference(expression='/orgs/org1/sources/source/concepts/concept/')
        reference.full_clean()
        CollectionVersion.persist_changes(version, col_reference=reference)
        self.assertEquals(len(version.concepts), 1)
        self.assertEquals(len(version.references), 1)

    def test_add_valid_mapping_expression_to_collection_positive(self):
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

        (from_concept, errors) = create_concept(mnemonic="fromConcept", user=self.user1, source=source)
        (to_concept, errors) = create_concept(mnemonic="toConcept", user=self.user1, source=source)

        mapping = Mapping(
            map_type='Same As',
            from_concept=from_concept,
            to_concept=to_concept,
            external_id='mapping',
        )
        kwargs = {
            'parent_resource': source,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)

        version = CollectionVersion.for_base_object(self.collection1, 'version1')
        reference = CollectionReference(
            expression='/orgs/org1/sources/source/mappings/' + Mapping.objects.filter()[0].id + '/')
        reference.full_clean()
        CollectionVersion.persist_changes(version, col_reference=reference)
        self.assertEquals(len(version.mappings), 1)
