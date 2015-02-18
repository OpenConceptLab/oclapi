"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
from urlparse import urlparse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from django.test import TestCase, Client
from django.test.client import MULTIPART_CONTENT, FakePayload
from django.utils.encoding import force_str
from concepts.models import Concept
from mappings.models import Mapping
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from oclapi.utils import add_user_to_org
from orgs.models import Organization
from sources.models import Source, SourceVersion
from users.models import UserProfile


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


class MappingBaseTest(TestCase):

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
            'creator': self.user1,
            'parent_resource': self.userprofile1
        }
        Source.persist_new(self.source1, **kwargs)
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
            'creator': self.user1,
            'parent_resource': self.org2,
        }
        Source.persist_new(self.source2, **kwargs)
        self.source2 = Source.objects.get(id=self.source2.id)

        self.concept1 = Concept(
            mnemonic='concept1',
            updated_by=self.user1,
            parent=self.source1,
            concept_class='First',
        )
        kwargs = {
            'creator': self.user1,
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept1, **kwargs)

        self.concept2 = Concept(
            mnemonic='concept2',
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Second',
        )
        kwargs = {
            'creator': self.user1,
            'parent_resource': self.source1,
        }
        Concept.persist_new(self.concept2, **kwargs)

        self.concept3 = Concept(
            mnemonic='concept3',
            updated_by=self.user1,
            parent=self.source2,
            concept_class='Third',
        )
        kwargs = {
            'creator': self.user1,
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept3, **kwargs)


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

        with self.assertRaises(ValidationError):
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
        self.assertTrue(mapping.id in source_version.mappings)

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
        self.assertTrue(mapping.id in source_version.mappings)

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
        self.assertTrue(mapping.id in source_version.mappings)

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
        self.assertTrue(mapping.id in source_version.mappings)

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
        self.assertTrue(mapping.id in version1.mappings)

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
        self.assertTrue(mapping.id in source_version.mappings)

        mapping.to_concept = self.concept3
        errors = Mapping.persist_changes(mapping, self.user1)
        self.assertEquals(0, len(errors))
        mapping = Mapping.objects.get(external_id='mapping1')

        self.assertEquals(self.concept3, mapping.to_concept)
        self.assertNotEquals(to_concept, mapping.to_concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(mapping.id in source_version.mappings)

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
        self.assertTrue(mapping.id in source_version.mappings)

        mapping.to_concept = self.concept3
        errors = Mapping.persist_changes(mapping, None)
        self.assertEquals(1, len(errors))
        self.assertTrue('updated_by' in errors)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.mappings))
        self.assertTrue(mapping.id in source_version.mappings)

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


class MappingCreateViewTest(MappingBaseTest):

    def test_mappings_create_negative__no_params(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_from_concept(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As'
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_map_type(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'from_concept_url': self.concept1.url
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_negative__no_to_concept(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
        }
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)

    def test_mappings_create_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())
        mapping = Mapping.objects.get(external_id='mapping1')
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])

    def test_mappings_create_positive__type2(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__both_types(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__self_mapping(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept1.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 400)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__not_authorized(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 404)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__other_user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user2.username,
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 404)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_positive__org_owner(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 201)
        self.assertTrue(Mapping.objects.filter(external_id='mapping1').exists())

    def test_mappings_create_negative__other_org_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())
        response = self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.assertEquals(response.status_code, 403)
        self.assertFalse(Mapping.objects.filter(external_id='mapping1').exists())


class MappingViewsTest(MappingBaseTest):
    client_class = OCLClient

    def setUp(self):
        super(MappingViewsTest, self).setUp()
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping1',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping1 = Mapping.objects.get(external_id='mapping1')

        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_source_url': self.source1.url,
            'to_concept_code': '10101',
            'to_concept_name': 'binary',
            'external_id': 'mapping2',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping2 = Mapping.objects.get(external_id='mapping2')

        # Create a new source
        self.source3 = Source(
            name='source3',
            mnemonic='source3',
            full_name='Source Three',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source3.com',
            description='This is the first third source',
        )
        kwargs = {
            'creator': self.user1,
            'parent_resource': self.userprofile1
        }

        Source.persist_new(self.source3, **kwargs)
        self.source3 = Source.objects.get(id=self.source3.id)
        self.source_version1 = SourceVersion.get_latest_version_of(self.source3)

        # Create a new version of the source
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
        }
        data = {
            'id': '2.0',
            'released': True
        }
        self.client.post(reverse('sourceversion-list', kwargs=kwargs), data)
        # Create a mapping in the latest version
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic
        }
        data = {
            'map_type': 'More specific than',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping4',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping4 = Mapping.objects.get(external_id='mapping4')
        self.source_version2 = SourceVersion.get_latest_version_of(self.source3)
        self.assertNotEquals(self.source_version1.id, self.source_version2.id)

        # Login as user2 who belongs to org2
        self.client.logout()
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        data = {
            'map_type': 'Same As',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping3',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping3 = Mapping.objects.get(external_id='mapping3')

        # Create a new source
        self.source4 = Source(
            name='source4',
            mnemonic='source4',
            full_name='Source Four',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source4.com',
            description='This is the fourth third source',
        )
        kwargs = {
            'creator': self.user2,
            'parent_resource': self.org2
        }
        Source.persist_new(self.source4, **kwargs)
        self.source4 = Source.objects.get(id=self.source4.id)
        self.source4_version1 = SourceVersion.get_latest_version_of(self.source4)

        # Create a new version of the source
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
        }
        data = {
            'id': '2.0',
            'released': True
        }
        self.client.post(reverse('sourceversion-list', kwargs=kwargs), data)
        # Create a mapping in the latest version
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic
        }
        data = {
            'map_type': 'Less specific than',
            'from_concept_url': self.concept1.url,
            'to_concept_url': self.concept2.url,
            'external_id': 'mapping5',
        }
        self.client.post(reverse('mapping-list', kwargs=kwargs), data)
        self.mapping5 = Mapping.objects.get(external_id='mapping5')
        self.source4_version2 = SourceVersion.get_latest_version_of(self.source4)
        self.assertNotEquals(self.source4_version1.id, self.source4_version2.id)

    def test_mappings_list_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_mappings_list_positive__latest_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_positive__explicit_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic,
            'version': self.source_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_negative__explicit_version(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

    def test_mappings_list_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_mappings_list_positive__explicit_user_and_version(self):
        mapping = self.mapping4
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_negative__explicit_user_and_version(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'user': self.user1.username,
            'source': self.source3.mnemonic,
            'version': self.source_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

    def test_mappings_list_positive__org_owner(self):
        mapping = self.mapping3
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_positive__explicit_org_and_version(self):
        mapping = self.mapping5
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
            'version': self.source4_version2.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content_list = json.loads(response.content)
        self.assertEquals(1, len(content_list))
        content = content_list[0]
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.url, content['url'])

    def test_mappings_list_negative__explicit_org_and_version(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source4.mnemonic,
            'version': self.source4_version1.mnemonic,
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(0, len(content))

    def test_mappings_get_positive(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1

        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_get_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1

        kwargs = {
            'user': self.user1,
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_get_positive__org_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping3
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'mapping': mapping.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.resource_type(), content['type'])
        self.assertEquals(mapping.id, content['id'])
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals(mapping.from_source_owner, content['from_source_owner'])
        self.assertEquals(mapping.from_source_owner_type, content['from_source_owner_type'])
        self.assertEquals(mapping.from_source_name, content['from_source_name'])
        self.assertEquals(mapping.from_source_url, content['from_source_url'])
        self.assertEquals(mapping.from_concept_code, content['from_concept_code'])
        self.assertEquals(mapping.from_concept_name, content['from_concept_name'])
        self.assertEquals(mapping.from_concept_url, content['from_concept_url'])
        self.assertEquals(mapping.to_source_owner, content['to_source_owner'])
        self.assertEquals(mapping.to_source_owner_type, content['to_source_owner_type'])
        self.assertEquals(mapping.to_source_name, content['to_source_name'])
        self.assertEquals(mapping.to_source_url, content['to_source_url'])
        self.assertEquals(mapping.get_to_concept_code(), content['to_concept_code'])
        self.assertEquals(mapping.get_to_concept_name(), content['to_concept_name'])
        self.assertEquals(mapping.to_concept_url, content['to_concept_url'])
        self.assertEquals(mapping.source, content['source'])
        self.assertEquals(mapping.owner, content['owner'])
        self.assertEquals(mapping.owner_type, content['owner_type'])
        self.assertEquals(mapping.url, content['url'])
        self.assertTrue(content['created_at'] in mapping.created_at.isoformat())
        self.assertTrue(content['updated_at'] in mapping.updated_at.isoformat())
        self.assertEquals(mapping.created_by, content['created_by'])
        self.assertEquals(mapping.updated_by, content['updated_by'])

    def test_mappings_update_positive(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else'
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

    def test_mappings_update_positive__user_owner(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        kwargs = {
            'user': self.user1.username,
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else'
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping1')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

    def test_mappings_update_positive__org_owner(self):
        self.client.login(username='user2', password='user2')
        mapping = self.mapping3
        kwargs = {
            'org': self.org2.mnemonic,
            'source': self.source2.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'map_type': 'Something Else'
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(mapping.external_id, content['external_id'])
        self.assertNotEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

        mapping = Mapping.objects.get(external_id='mapping3')
        self.assertEquals(mapping.map_type, content['map_type'])
        self.assertEquals('Something Else', content['map_type'])

    def test_mappings_update_negative__bad_url(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        from_concept = mapping.from_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'from_concept_url': 'http://does.not.exist/'
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        content = json.loads(response.content)
        self.assertTrue('from_concept_url' in content)

        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(from_concept, mapping.from_concept)

    def test_mappings_update_negative__self_reference(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        to_concept = mapping.to_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'to_concept_url': mapping.from_concept_url
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(to_concept, mapping.to_concept)

    def test_mappings_update_negative__mixed_types(self):
        self.client.login(username='user1', password='user1')
        mapping = self.mapping1
        to_concept = mapping.to_concept
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': mapping.mnemonic,
        }
        data = {
            'to_concept_code': '10101'
        }
        response = self.client.put(reverse('mapping-detail', kwargs=kwargs), data, content_type=MULTIPART_CONTENT)
        self.assertEquals(response.status_code, 400)
        mapping = Mapping.objects.get(id=mapping.id)
        self.assertEquals(to_concept, mapping.to_concept)

    def test_mappings_delete_positive(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic
        }
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

        kwargs.update({'mapping': self.mapping1.mnemonic})
        response = self.client.delete(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 204)

        mapping = Mapping.objects.get(id=self.mapping1.id)
        self.assertTrue(mapping.retired)

        del(kwargs['mapping'])
        response = self.client.get(reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(1, len(content))

        response = self.client.get("%s?include_retired=true" % reverse('mapping-list', kwargs=kwargs))
        self.assertEquals(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEquals(2, len(content))

    def test_mappings_delete_negative__not_found(self):
        self.client.login(username='user1', password='user1')
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': '12345',
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)

    def test_mappings_delete_negative__not_allowed(self):
        self.client.login(username='user2', password='user2')
        kwargs = {
            'source': self.source1.mnemonic,
            'mapping': self.mapping1.mnemonic,
        }
        response = self.client.get(reverse('mapping-detail', kwargs=kwargs))
        self.assertEquals(response.status_code, 404)