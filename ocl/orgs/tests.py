"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from oclapi.utils import add_user_to_org, remove_user_from_org
from orgs.models import Organization, ORG_OBJECT_TYPE
from sources.models import Source
from users.models import UserProfile
from test_helper.base import OclApiBaseTestCase, create_organization


class OrganizationTestCase(OclApiBaseTestCase):
    def test_create_organization_positive(self):
        self.assertFalse(Organization.objects.filter(mnemonic='org1').exists())
        org = Organization(mnemonic='org1', name='My Organization', created_by='user1', updated_by='user1')
        org.full_clean()
        org.save()
        self.assertTrue(Organization.objects.filter(mnemonic='org1').exists())

    def test_create_organization_negative__no_name(self):
        with self.assertRaises(ValidationError):
            org = Organization(mnemonic='org1', created_by='user1', updated_by='user1')
            org.full_clean()
            org.save()

    def test_create_organization_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            org = Organization(name='My Organization', created_by='user1', updated_by='user1')
            org.full_clean()
            org.save()

    def test_organization_delete(self):
        org = Organization(mnemonic='org1', name='My Organization', created_by='user1', updated_by='user1')
        org.full_clean()
        org.save()
        org_id = org.id

        self.assertTrue(org.is_active)
        self.assertTrue(Organization.objects.filter(id=org_id).exists())
        org.soft_delete()
        self.assertFalse(org.is_active)
        self.assertTrue(Organization.objects.filter(id=org_id).exists())
        org.delete()
        self.assertFalse(Organization.objects.filter(id=org_id).exists())

    def test_resource_type(self):
        org = Organization(mnemonic='org1', name='My Organization', created_by='user1', updated_by='user1')
        org.full_clean()
        org.save()

        self.assertEquals(ORG_OBJECT_TYPE, org.resource_type())

    def test_org_num_members(self):
        org = Organization(mnemonic='org1', name='My Organization', created_by='user1', updated_by='user1')
        org.full_clean()
        org.save()

        self.assertEquals(0, org.num_members)
        org.members.append(1)
        self.assertEquals(1, org.num_members)
        org.members.remove(1)
        self.assertEquals(0, org.num_members)

    def test_public_sources(self):
        user = User.objects.create(
            username='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User'
        )

        org = Organization(mnemonic='org1', name='My Organization', created_by='user1', updated_by='user1')
        org.full_clean()
        org.save()

        self.assertEquals(0, org.public_sources)
        Source.objects.create(
            mnemonic='source1',
            parent=org,
            name='Source One',
        )
        self.assertEquals(1, org.public_sources)

        org2 = Organization(mnemonic='org2', name='Your Organization', created_by='user1', updated_by='user1')
        org2.full_clean()
        org2.save()

        Source.objects.create(
            mnemonic='source1',
            parent=org2,
            name='Source One',
        )
        self.assertEquals(1, org.public_sources)
        Source.objects.create(
            mnemonic='source2',
            parent=org,
            name='Source Two',
        )
        self.assertEquals(2, org.public_sources)

    def test_add_user_to_org(self):
        user = User.objects.create(
            username='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User'
        )
        userprofile = UserProfile.objects.create(user=user, mnemonic='user1', created_by='user1', updated_by='user1')
        org = Organization.objects.create(name='org1', mnemonic='org1', created_by='user1', updated_by='user1')

        self.assertEquals(0, userprofile.orgs)
        self.assertEquals(0, org.num_members)

        add_user_to_org(userprofile, org)

        self.assertEquals(1, userprofile.orgs)
        self.assertEquals(1, org.num_members)

        self.assertEquals(org.id, userprofile.organizations[0])
        self.assertEquals(userprofile.id, org.members[0])

        remove_user_from_org(userprofile, org)

        self.assertEquals(0, userprofile.orgs)
        self.assertEquals(0, org.num_members)

    def test_create_org_special_characters(self):
        # period in mnemonic
        org = create_organization(name='test', mnemonic='org.1')
        self.assertEquals('org.1', org.mnemonic)

        # hyphen in mnemonic
        org = create_organization(name='test', mnemonic='org-1')
        self.assertEquals('org-1', org.mnemonic)

        # underscore in mnemonic
        org = create_organization(name='test', mnemonic='org_1')
        self.assertEquals('org_1', org.mnemonic)

        # all characters in mnemonic
        org = create_organization(name='test', mnemonic='org.1_2-3')
        self.assertEquals('org.1_2-3', org.mnemonic)

        # test validation error
        with self.assertRaises(ValidationError):
            org = Organization(name='test', mnemonic='org@1')
            org.full_clean()
            org.save()
