from django.contrib.auth.models import User
from oclapi.models import ACCESS_TYPE_EDIT
from orgs.models import Organization
from sources.models import Source, SourceVersion
from users.models import UserProfile
from test_helper.base import OclApiBaseTestCase
from oclapi.utils import compact, extract_values

class ResourceVersionModelBaseTest(OclApiBaseTestCase):

    def setUp(self):
        self.user = User.objects.create(username='user', email='user@test.com', last_name='One', first_name='User')
        self.profile = UserProfile.objects.create(user=self.user, mnemonic='user')
        self.org = Organization.objects.create(name='org', mnemonic='org')

        self.source = Source(name='source',
            mnemonic='source',
            full_name='Source One',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source.com',
            description='This is the first test source'
        )

        kwargs = {
            'parent_resource': self.profile
        }
        Source.persist_new(self.source, self.user, **kwargs)
        self.source = Source.objects.get(id=self.source.id)


class ResourceVersionTest(ResourceVersionModelBaseTest):

    def test_get_head_of(self):
        self.assertEquals(SourceVersion.get_head_of(self.source), self.source.get_version_model().objects.get(mnemonic='HEAD', versioned_object_id=self.source.id))

    def test_get_head_of_when_head_does_not_exist(self):
        source = Source(name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source2.com',
            description='This is not the first test source'
        )

        kwargs = {
            'parent_resource': self.profile
        }
        Source.persist_new(source, self.user, **kwargs)
        source.get_version_model().objects.get(mnemonic='HEAD', versioned_object_id=source.id).delete()
        self.assertIsNone(SourceVersion.get_head_of(source))

    def test_get_latest_version_of(self):
        latest_version_identity = 'version'
        expected_latest_source_version = SourceVersion(
            name=latest_version_identity,
            mnemonic=latest_version_identity,
            versioned_object=self.source,
            released=True,
            created_by=self.user,
            updated_by=self.user,
        )
        expected_latest_source_version.full_clean()
        expected_latest_source_version.save()

        self.assertEquals(SourceVersion.get_latest_version_of(self.source).name, latest_version_identity)

    def test_get_latest_version_when_no_version_exist(self):
        source = Source(name='source2',
            mnemonic='source2',
            full_name='Source Two',
            source_type='Dictionary',
            public_access=ACCESS_TYPE_EDIT,
            default_locale='en',
            supported_locales=['en'],
            website='www.source2.com',
            description='This is not the first test source'
        )

        kwargs = {
            'parent_resource': self.profile
        }
        Source.persist_new(source, self.user, **kwargs)
        source.get_version_model().objects.get(mnemonic='HEAD', versioned_object_id=source.id).delete()
        self.assertFalse(SourceVersion.objects.filter(versioned_object_id=source.id).exists())
        self.assertIsNone(SourceVersion.get_latest_version_of(source))


class UtilsTest(OclApiBaseTestCase):
    def test_compact(self):
        self.assertListEqual(compact([1, 2, None, 3]), [1, 2, 3])
        self.assertListEqual(compact([None, 2, None, 3]), [2, 3])
        self.assertListEqual(compact([None]), [])
        self.assertListEqual(compact([""]), [])

    def test_extract_values(self):
        self.assertListEqual(extract_values({'k1': 1, 'k2': '2', 'k3': None, 'k4': 'foobar'}, ['k2', 'k1', 'k3']), ['2', 1, None])
        self.assertListEqual(extract_values({'k1': '2'}, ['k1']), ['2'])
        self.assertListEqual(extract_values({'k1': 1}, ['k1']), [1])
