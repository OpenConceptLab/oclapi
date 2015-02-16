"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User

from django.test import TestCase
from concepts.models import Concept
from mappings.models import Mapping
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from orgs.models import Organization
from sources.models import Source
from users.models import UserProfile


class MappingBaseTest(TestCase):

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
            external_id='mapping1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=self.concept1,
            to_concept=self.concept2,
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
