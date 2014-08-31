"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from sources.models import Source
from users.models import UserProfile, USER_OBJECT_TYPE


class UserProfileTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(
            username='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User'
        )

    def test_create_userprofile_positive(self):
        self.assertFalse(UserProfile.objects.filter(mnemonic='user1').exists())
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()
        self.assertTrue(UserProfile.objects.filter(mnemonic='user1').exists())

    def test_create_userprofile_negative__no_user(self):
        with self.assertRaises(ValidationError):
            user = UserProfile(mnemonic='user1', created_by=self.user1, updated_by=self.user1)
            user.full_clean()
            user.save()

    def test_create_userprofile_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            user = UserProfile(user=self.user1, created_by=self.user1, updated_by=self.user1)
            user.full_clean()
            user.save()

    def test_profile_name_overrides_user_name(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals("%s %s" % (self.user1.first_name, self.user1.last_name), user.name)
        user.full_name = 'John Q. Test'
        self.assertEquals('John Q. Test', user.name)

    def test_resource_type(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals(USER_OBJECT_TYPE, user.resource_type())

    def test_mnemonic_overrides_username(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals(self.user1.username, user.username)
        user.mnemonic = 'johnnytest'
        self.assertEquals('johnnytest', user.username)

    def test_inherits_email_from_user(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals(self.user1.email, user.email)

    def test_user_orgs(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals(0, user.orgs)
        user.organizations.append(1)
        self.assertEquals(1, user.orgs)
        user.organizations.remove(1)
        self.assertEquals(0, user.orgs)

    def test_user_public_sources(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        self.assertEquals(0, user.public_sources)
        Source.objects.create(
            mnemonic='source1',
            owner=self.user1,
            parent=user,
            name='Source One',
        )
        self.assertEquals(1, user.public_sources)
        Source.objects.create(
            mnemonic='source1',
            owner=self.user1,
            parent=self.user1,
            name='Source One',
        )
        self.assertEquals(1, user.public_sources)
        Source.objects.create(
            mnemonic='source2',
            owner=self.user1,
            parent=user,
            name='Source Two',
        )
        self.assertEquals(2, user.public_sources)

    def test_delete(self):
        user = UserProfile(user=self.user1, mnemonic='user1', created_by=self.user1, updated_by=self.user1)
        user.full_clean()
        user.save()

        user_id = user.id
        self.assertTrue(user.is_active)
        self.assertTrue(UserProfile.objects.filter(id=user_id).exists())
        user.soft_delete()
        self.assertFalse(user.is_active)
        self.assertTrue(UserProfile.objects.filter(id=user_id).exists())
        user.delete()
        self.assertFalse(UserProfile.objects.filter(id=user_id).exists())