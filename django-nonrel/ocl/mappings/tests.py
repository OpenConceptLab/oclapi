"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from urlparse import urlparse

from django.contrib.contenttypes.models import ContentType

from concepts.models import Concept, ConceptVersion, LocalizedText
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import Client
from django.test.client import MULTIPART_CONTENT, FakePayload
from django.utils.encoding import force_str
from mappings.models import Mapping, MappingVersion
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from oclapi.utils import add_user_to_org
from orgs.models import Organization
from sources.models import Source, SourceVersion
from users.models import UserProfile
from collection.models import Collection
from test_helper.base import OclApiBaseTestCase
from unittest import skip

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


class MappingBaseTest(OclApiBaseTestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='user1',
            last_name='One',
            first_name='User'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='user2',
            last_name='Two',
            first_name='User'
        )

        self.userprofile1 = UserProfile.objects.create(user=self.user1, mnemonic='user1')
        self.userprofile2 = UserProfile.objects.create(user=self.user2, mnemonic='user2')

        self.org1 = Organization.objects.create(name='org1', mnemonic='org1')
        self.org2 = Organization.objects.create(name='org2', mnemonic='org2')
        add_user_to_org(self.userprofile2, self.org2)

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
        )
        kwargs = {
            'parent_resource': self.userprofile1
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
        )
        kwargs = {
            'parent_resource': self.org2,
        }
        Source.persist_new(self.source2, self.user1, **kwargs)
        self.source2 = Source.objects.get(id=self.source2.id)

        self.name = LocalizedText.objects.create(name='Fred', locale='en')

        self.concept1 = Concept(
            mnemonic='concept1',
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, self.user1, **kwargs)

        self.concept2 = Concept(
            mnemonic='concept2',
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Second',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept2, self.user1, **kwargs)

        self.concept3 = Concept(
            mnemonic='concept3',
            updated_by=self.user1,
            parent=self.source2,
            concept_class='Third',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept3, self.user1, **kwargs)

        self.concept4 = Concept(
            mnemonic='concept4',
            updated_by=self.user2,
            parent=self.source2,
            concept_class='Fourth',
            names=[self.name],
        )
        kwargs = {
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept4, self.user1, **kwargs)

class MappingVersionBaseTest(MappingBaseTest):
    def setUp(self):
        super(MappingVersionBaseTest, self).setUp()
        self.mapping1 = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='versionmapping1',
        )
        self.mapping1.full_clean()
        self.mapping1.save()

class MappingTest(MappingBaseTest):

    def test_create_mapping_positive(self):
        mapping = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        mapping.full_clean()
        mapping.save()

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(ACCESS_TYPE_VIEW, mapping.public_access)
        self.assertEquals('user1', mapping.created_by)
        self.assertEquals('user1', mapping.updated_by)
        self.assertEquals(self.source1, mapping.parent)
        self.assertEquals('Same As', mapping.map_type)
        self.assertEquals(self.concept1, mapping.from_concept)
        self.assertEquals(self.concept2, mapping.to_concept)
        self.assertEquals(self.source1, mapping.from_source)
        self.assertEquals(self.source1.owner_name, mapping.from_source_owner)
        self.assertEquals(self.source1.mnemonic, mapping.from_source_name)
        self.assertEquals(self.source1, mapping.get_to_source())
        self.assertEquals(self.source1.owner_name, mapping.to_source_owner)
        self.assertEquals(self.concept2.mnemonic, mapping.get_to_concept_code())
        self.assertEquals(self.concept2.display_name, mapping.get_to_concept_name())

    def test_create_mapping_negative__no_created_by(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__no_updated_by(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__no_map_type(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__no_from_concept(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__no_to_concept(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__two_to_concepts(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                to_concept_code='code',
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__self_mapping(self):
        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept1,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__same_mapping_type1(self):
        mapping = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        mapping.full_clean()
        mapping.save()

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

        with self.assertRaises(ValidationError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
            )
            mapping.full_clean()
            mapping.save()

    def test_create_mapping_negative__same_mapping_type2(self):
        mapping = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_source=self.source1,
            to_concept_code='code',
            to_concept_name='name',
            external_id='mapping1',
        )
        mapping.full_clean()
        mapping.save()

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(ACCESS_TYPE_VIEW, mapping.public_access)
        self.assertEquals('user1', mapping.created_by)
        self.assertEquals('user1', mapping.updated_by)
        self.assertEquals(self.source1, mapping.parent)
        self.assertEquals('Same As', mapping.map_type)
        self.assertEquals(self.concept1, mapping.from_concept)
        self.assertIsNone(mapping.to_concept)
        self.assertEquals(self.source1, mapping.from_source)
        self.assertEquals(self.source1.owner_name, mapping.from_source_owner)
        self.assertEquals(self.source1.mnemonic, mapping.from_source_name)
        self.assertEquals(self.source1, mapping.get_to_source())
        self.assertEquals(self.source1.owner_name, mapping.to_source_owner)
        self.assertEquals('code', mapping.get_to_concept_code())
        self.assertEquals('name', mapping.get_to_concept_name())

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

        with self.assertRaises(IntegrityError):
            mapping = Mapping(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_source=self.source1,
                to_concept_code='code',
                to_concept_name='name',
                external_id='mapping1',
            )

            mapping.full_clean()
            mapping.save()

    def test_mapping_access_changes_with_source(self):
        public_access = self.source1.public_access
        mapping = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            public_access=public_access,
            external_id='mapping1',
        )
        mapping.full_clean()
        mapping.save()

        self.assertEquals(self.source1.public_access, mapping.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

        mapping = Mapping.objects.get(id=mapping.id)
        self.assertNotEquals(public_access, self.source1.public_access)
        self.assertEquals(self.source1.public_access, mapping.public_access)

class MappingVersionTest(MappingVersionBaseTest):

    def test_create_mapping_positive(self):
        mapping_version = MappingVersion(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mappingversion1',
            versioned_object_id=self.mapping1.id,
            mnemonic='tempid',
            versioned_object_type=ContentType.objects.get_for_model(Mapping),
        )
        mapping_version.full_clean()
        mapping_version.save()

        self.assertTrue(MappingVersion.objects.filter(versioned_object_id = self.mapping1.id).exists())
        mapping_version = MappingVersion.objects.get(versioned_object_id = self.mapping1.id)
        self.assertEquals(ACCESS_TYPE_VIEW, mapping_version.public_access)
        self.assertEquals('user1', mapping_version.created_by)
        self.assertEquals('user1', mapping_version.updated_by)
        self.assertEquals(self.source1, mapping_version.parent)
        self.assertEquals('Same As', mapping_version.map_type)
        self.assertEquals(self.concept1, mapping_version.from_concept)
        self.assertEquals(self.concept2, mapping_version.to_concept)
        self.assertEquals(self.source1, mapping_version.from_source)
        self.assertEquals(self.source1.owner_name, mapping_version.from_source_owner)
        self.assertEquals(self.source1.mnemonic, mapping_version.from_source_name)
        self.assertEquals(self.source1, mapping_version.get_to_source())
        self.assertEquals(self.source1.owner_name, mapping_version.to_source_owner)
        self.assertEquals(self.concept2.mnemonic, mapping_version.get_to_concept_code())
        self.assertEquals(self.concept2.display_name, mapping_version.get_to_concept_name())

    def test_create_mapping_negative__no_created_by(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping111',
                versioned_object_id=self.mapping1.id,
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_create_mapping_negative__no_updated_by(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                created_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
                versioned_object_id=self.mapping1.id,
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_create_mapping_negative__no_parent(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                created_by=self.user1,
                updated_by=self.user1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
                versioned_object_id=self.mapping1.id,
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_create_mapping_negative__no_map_type(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
                versioned_object_id=self.mapping1.id,
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_create_mapping_negative__no_from_concept(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                to_concept=self.concept2,
                external_id='mapping1',
                versioned_object_id=self.mapping1.id,
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_create_mapping_negative__no_version_object(self):
        with self.assertRaises(ValidationError):
            mapping_version = MappingVersion(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                map_type='Same As',
                from_concept=self.concept1,
                to_concept=self.concept2,
                external_id='mapping1',
                versioned_object_type=ContentType.objects.get_for_model(Mapping),
                mnemonic='tempid'
            )
            mapping_version.full_clean()
            mapping_version.save()

    def test_mapping_access_changes_with_source(self):
        public_access = self.source1.public_access
        mapping_version = MappingVersion(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            public_access=public_access,
            external_id='mapping1',
            versioned_object_id=self.mapping1.id,
            versioned_object_type=ContentType.objects.get_for_model(Mapping),
            mnemonic='tempid'
        )
        mapping_version.full_clean()
        mapping_version.save()

        self.assertEquals(self.source1.public_access, mapping_version.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

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
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)

        fromConcept = Concept(
            mnemonic='fromConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(fromConcept, self.user1, **kwargs)

        toConcept = Concept(
            mnemonic='toConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(toConcept, self.user1, **kwargs)

        mapping = Mapping(
            map_type='foobar',
            from_concept=fromConcept,
            to_concept=toConcept,
            external_id='mapping',
        )
        kwargs = {
            'parent_resource': source,
        }

        Mapping.persist_new(mapping, self.user1, **kwargs)

        from_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(mnemonic=fromConcept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(mnemonic=concept1.mnemonic).mnemonic + '/'
        mapping = Mapping.objects.filter()[1]
        mapping_reference = '/orgs/org1/sources/source/mappings/' + mapping.id + '/'

        references = [concept1_reference, from_concept_reference, mapping_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()
        mv = MappingVersion.objects.get(versioned_object_id=mapping.id, is_latest_version=True)
        self.assertEquals(mv.collection_version_ids, [Collection.objects.get(mnemonic=collection.mnemonic).get_head().id])

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
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(concept1, self.user1, **kwargs)

        fromConcept = Concept(
            mnemonic='fromConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(fromConcept, self.user1, **kwargs)

        toConcept = Concept(
            mnemonic='toConcept',
            created_by=self.user1,
            updated_by=self.user1,
            parent=source,
            concept_class='First',
            names=[LocalizedText.objects.create(name='User', locale='es')],
        )
        kwargs = {
            'parent_resource': source,
        }
        Concept.persist_new(toConcept, self.user1, **kwargs)

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

        from_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(mnemonic=fromConcept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(mnemonic=concept1.mnemonic).mnemonic + '/'
        mapping = Mapping.objects.filter()[1]
        mapping_reference = '/orgs/org1/sources/source/mappings/' + mapping.id + '/'

        references = [concept1_reference, from_concept_reference, mapping_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()
        mv = MappingVersion.objects.get(versioned_object_id=mapping.id, is_latest_version=True)
        self.assertEquals(mv.collection_version_ids, [Collection.objects.get(mnemonic=collection.mnemonic).get_head().id])

class MappingClassMethodsTest(MappingBaseTest):

    def test_persist_new_positive(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(self.source1.public_access, mapping.public_access)
        self.assertEquals('user1', mapping.created_by)
        self.assertEquals('user1', mapping.updated_by)
        self.assertEquals(self.source1, mapping.parent)
        self.assertEquals('Same As', mapping.map_type)
        self.assertEquals(self.concept1, mapping.from_concept)
        self.assertEquals(self.concept2, mapping.to_concept)
        self.assertEquals(self.source1, mapping.from_source)
        self.assertEquals(self.source1.owner_name, mapping.from_source_owner)
        self.assertEquals(self.source1.mnemonic, mapping.from_source_name)
        self.assertEquals(self.source1, mapping.get_to_source())
        self.assertEquals(self.source1.owner_name, mapping.to_source_owner)
        self.assertEquals(self.concept2.mnemonic, mapping.get_to_concept_code())
        self.assertEquals(self.concept2.display_name, mapping.get_to_concept_name())

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

    def test_persist_new_version_created_positive(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertTrue(MappingVersion.objects.filter(versioned_object_id=mapping.id, is_latest_version=True).exists())
        mapping_version = MappingVersion.objects.get(versioned_object_id=mapping.id, is_latest_version=True)
        self.assertEquals(self.source1.public_access, mapping_version.public_access)
        self.assertEquals('user1', mapping_version.created_by)
        self.assertEquals('user1', mapping_version.updated_by)
        self.assertEquals(self.source1, mapping_version.parent)
        self.assertEquals('Same As', mapping_version.map_type)
        self.assertEquals(self.concept1, mapping_version.from_concept)
        self.assertEquals(self.concept2, mapping_version.to_concept)
        self.assertEquals(self.source1, mapping_version.from_source)
        self.assertEquals(self.source1.owner_name, mapping_version.from_source_owner)
        self.assertEquals(self.source1.mnemonic, mapping_version.from_source_name)
        self.assertEquals(self.source1, mapping_version.get_to_source())
        self.assertEquals(self.source1.owner_name, mapping_version.to_source_owner)
        self.assertEquals(self.concept2.mnemonic, mapping_version.get_to_concept_code())
        self.assertEquals(self.concept2.display_name, mapping_version.get_to_concept_name())

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)


    def test_persist_new_negative__no_creator(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, None, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('non_field_errors' in errors)
        non_field_errors = errors['non_field_errors']
        self.assertEquals(1, len(non_field_errors))
        self.assertTrue('creator' in non_field_errors[0])

        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.mappings))

    def test_persist_new_negative__no_parent(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {}
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertTrue('non_field_errors' in errors)
        non_field_errors = errors['non_field_errors']
        self.assertEquals(1, len(non_field_errors))
        self.assertTrue('parent' in non_field_errors[0])

        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.mappings))

    def test_persist_new_negative__same_mapping(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        mv = MappingVersion.objects.get(versioned_object_id=mapping.id)
        self.assertTrue(mv.id in source_version.mappings)

        # Repeat with same concepts
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping2',
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(1, len(errors))
        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)
        non_field_errors = errors['__all__']
        self.assertEquals(1, len(non_field_errors))
        self.assertTrue('already exists' in non_field_errors[0])
        self.assertEquals(1, len(source_version.mappings))

    def test_persist_new_positive__same_mapping_different_source(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

        # Repeat with same concepts
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping2',
        )
        kwargs = {
            'parent_resource': self.source2,
        }
        source_version = SourceVersion.get_latest_version_of(self.source2)
        self.assertEquals(0, len(source_version.mappings))
        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertTrue(Mapping.objects.filter(external_id='mapping2').exists())
        mapping = Mapping.objects.get(external_id='mapping2')

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

    def test_persist_new_positive__earlier_source_version(self):
        version1 = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(version1.mappings))

        version2 = SourceVersion.for_base_object(self.source1, label='version2')
        version2.save()
        self.assertEquals(0, len(version2.mappings))

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))

        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        kwargs = {
            'parent_resource': self.source1,
            'parent_resource_version': version1,
        }

        errors = Mapping.persist_new(mapping, self.user1, **kwargs)
        self.assertEquals(0, len(errors))
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')

        version1 = SourceVersion.objects.get(id=version1.id)
        self.assertEquals(1, len(version1.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in version1.mappings)

        version2 = SourceVersion.objects.get(id=version2.id)
        self.assertEquals(0, len(version2.mappings))
        latest_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(latest_version.mappings))

    def test_persist_persist_changes_positive(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        mapping = Mapping.objects.get(external_id='mapping1')
        to_concept = mapping.to_concept

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

        mapping.to_concept = self.concept3
        errors = Mapping.persist_changes(mapping, self.user1)
        self.assertEquals(0, len(errors))
        mapping = Mapping.objects.get(external_id='mapping1')

        self.assertEquals(self.concept3, mapping.to_concept)
        self.assertNotEquals(to_concept, mapping.to_concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        mv  = MappingVersion.objects.filter(versioned_object_id=mapping.id)
        self.assertTrue(mv[1].id in source_version.mappings)

    def test_persist_persist_changes_negative__no_updated_by(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        mapping = Mapping.objects.get(external_id='mapping1')

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

        mapping.to_concept = self.concept3
        errors = Mapping.persist_changes(mapping, None)
        self.assertEquals(1, len(errors))
        self.assertTrue('updated_by' in errors)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(MappingVersion.objects.get(versioned_object_id=mapping.id).id in source_version.mappings)

    def test_retire_positive(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertFalse(mapping.retired)

        retired = Mapping.retire(mapping, self.user1)
        self.assertTrue(retired)
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertTrue(mapping.retired)

    def test_retire_negative(self):
        mapping = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
            retired=True,
        )
        kwargs = {
            'parent_resource': self.source1,
        }
        Mapping.persist_new(mapping, self.user1, **kwargs)
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertTrue(mapping.retired)

        retired = Mapping.retire(mapping, self.user1)
        self.assertFalse(retired)
        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertTrue(mapping.retired)

    def test_edit_mapping_make_new_version_positive(self):
        mapping1 = Mapping(
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
            external_id='mapping1',
        )
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.mappings))
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Mapping.persist_new(mapping1, self.user1, **kwargs)
        self.assertEquals(0, len(errors))

        self.assertEquals(1,len(MappingVersion.objects.filter(versioned_object_id=mapping1.id)))

        mapping1.map_type='BROADER_THAN'
        Mapping.persist_changes(mapping1, self.user1)

        self.assertEquals(2, len(MappingVersion.objects.filter(versioned_object_id=mapping1.id)))

        old_version = MappingVersion.objects.get(versioned_object_id=mapping1.id, is_latest_version=False)

        new_version= MappingVersion.objects.get(versioned_object_id=mapping1.id, is_latest_version=True)

        self.assertFalse(old_version.is_latest_version)
        self.assertTrue(new_version.is_latest_version)
        self.assertEquals(new_version.map_type,'BROADER_THAN')
        self.assertEquals(old_version.map_type,'Same As')

