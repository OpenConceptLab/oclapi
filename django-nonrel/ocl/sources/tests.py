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
from sources.models import Source, DICTIONARY_SRC_TYPE, EDIT_ACCESS_TYPE
from users.models import UserProfile


class SourceTest(TestCase):

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
            parent_id=self.userprofile1.id)
        .exists())
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


