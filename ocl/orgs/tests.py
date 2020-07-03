"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from collection.models import Collection, CollectionVersion
from concepts.models import Concept, ConceptVersion
from oclapi.utils import add_user_to_org, remove_user_from_org
from orgs.models import Organization, ORG_OBJECT_TYPE
from sources.models import Source, SourceVersion
from users.models import UserProfile
from test_helper.base import OclApiBaseTestCase, create_organization, create_concept


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

    def test_delete_organization(self):
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

    def test_delete_organization_with_sources_and_collections(self):
        org = Organization(mnemonic='org1', name='My Organization', created_by=self.user, updated_by=self.user)
        org.full_clean()
        org.save()
        org_id = org.id

        org = Organization.objects.get(id=org.id)
        user1 = UserProfile.objects.get(mnemonic=self.user.username);
        org.members.append(user1.id)
        user1.organizations.append(org.id)
        org.save()
        user1.save()

        source = Source(name='source1', mnemonic='source1', full_name='Source One', parent=org, created_by=self.user, updated_by=self.user)
        source.full_clean()
        source.save()

        source2 = Source(name='source2', mnemonic='source2', full_name='Source Two', parent=org, created_by=self.user, updated_by=self.user)
        source2.full_clean()
        source2.save()

        source_version = SourceVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=source2,
            released=True,
            created_by=self.user,
            updated_by=self.user,
        )
        source_version.full_clean()
        source_version.save()

        source_version2 = SourceVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=source2,
            released=True,
            created_by=self.user,
            updated_by=self.user,
        )
        source_version2.full_clean()
        source_version2.save()

        collection = Collection.objects.create(name='collection1', mnemonic='collection1', created_by=self.user,
                                  updated_by=self.user, parent=org, external_id='EXTID1')

        collection_version = CollectionVersion(
            name='version1',
            mnemonic='version1',
            versioned_object=collection,
            released=True,
            created_by='user1',
            updated_by='user1',
        )
        collection_version.full_clean()
        collection_version.save()

        collection_version2 = CollectionVersion(
            name='version2',
            mnemonic='version2',
            versioned_object=collection,
            released=True,
            created_by=self.user,
            updated_by=self.user,
        )
        collection_version2.full_clean()
        collection_version2.save()

        collection2 = Collection.objects.create(name='collection2', mnemonic='collection2', created_by=self.user,
                                               updated_by=self.user, parent=org, external_id='EXTID2')

        self.assertTrue(Organization.objects.filter(id=org_id).exists())

        self.assertTrue(Source.objects.filter(id=source.id).exists())
        self.assertTrue(Source.objects.filter(id=source2.id).exists())

        self.assertTrue(SourceVersion.objects.filter(id=source_version.id).exists());
        self.assertTrue(SourceVersion.objects.filter(id=source_version2.id).exists());

        self.assertTrue(Collection.objects.filter(id=collection.id).exists())
        self.assertTrue(Collection.objects.filter(id=collection2.id).exists())

        self.assertTrue(CollectionVersion.objects.filter(id=collection_version.id).exists());
        self.assertTrue(CollectionVersion.objects.filter(id=collection_version2.id).exists());

        org.delete()
        self.assertFalse(Organization.objects.filter(id=org.id).exists())

        self.assertFalse(Source.objects.filter(id=source.id).exists())
        self.assertFalse(Source.objects.filter(id=source2.id).exists())

        self.assertFalse(SourceVersion.objects.filter(id=source_version.id).exists());
        self.assertFalse(SourceVersion.objects.filter(id=source_version2.id).exists());

        self.assertFalse(Collection.objects.filter(id=collection.id).exists())
        self.assertFalse(Collection.objects.filter(id=collection2.id).exists())

        self.assertFalse(CollectionVersion.objects.filter(id=collection_version.id).exists());
        self.assertFalse(CollectionVersion.objects.filter(id=collection_version2.id).exists());

        #should not delete member user
        self.assertTrue(UserProfile.objects.filter(mnemonic=self.user.username).exists());
        #should delete org from organizations on user
        self.assertFalse(org_id in UserProfile.objects.get(mnemonic=self.user.username).organizations)

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
