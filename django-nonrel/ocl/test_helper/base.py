import random

import string

from collection.models import CollectionVersion, Collection
from concepts.models import Concept, ConceptVersion, LocalizedText
from oclapi.models import ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from orgs.models import Organization
from sources.models import Source, SourceVersion
from users.models import UserProfile
from mappings.models import Mapping, MappingVersion
from django.contrib.auth.models import User
from django.test import TestCase


class OclApiBaseTestCase(TestCase):
    def tearDown(self):
        LocalizedText.objects.filter().delete()
        ConceptVersion.objects.filter().delete()
        Concept.objects.filter().delete()
        MappingVersion.objects.filter().delete()
        Mapping.objects.filter().delete()
        SourceVersion.objects.filter().delete()
        Source.objects.filter().delete()
        CollectionVersion.objects.filter().delete()
        Collection.objects.filter().delete()
        Organization.objects.filter().delete()
        UserProfile.objects.filter().delete()
        User.objects.filter().delete()


def generate_random_string(length=5):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))


def create_localized_text(name, locale='en', type='FULLY_SPECIFIED'):
    return LocalizedText.objects.create(name=name, locale=locale, type=type)


def create_user():
    suffix = generate_random_string()

    user = User.objects.create(
        username="test{0}".format(suffix),
        password="test{0}".format(suffix),
        email='user{0}@test.com'.format(suffix),
        first_name='Test',
        last_name='User'
    )

    UserProfile.objects.create(user=user, mnemonic='user{0}'.format(suffix))

    return user


def create_user_profile(user):
    suffix = generate_random_string()
    return UserProfile.objects.create(user=user, mnemonic='user{0}'.format(suffix))


def create_organization():
    suffix = generate_random_string()

    return Organization.objects.create(name='org{0}'.format(suffix), mnemonic='org{0}'.format(suffix))


def create_source(user, validation_schema=None, organization=None):
    suffix = generate_random_string()

    source = Source(
        name="source{0}".format(suffix),
        mnemonic="source{0}".format(suffix),
        full_name="Source {0}".format(suffix),
        source_type='Dictionary',
        public_access=ACCESS_TYPE_EDIT,
        default_locale='en',
        supported_locales=['en'],
        website='www.source.com',
        description='This is a test source',
        custom_validation_schema=validation_schema
    )

    if organization is not None:
        kwargs = {
            'parent_resource': organization
        }
    else:
        kwargs = {
            'parent_resource': UserProfile.objects.get(user=user)
        }

    Source.persist_new(source, user, **kwargs)

    return Source.objects.get(id=source.id)


def create_concept(user, source, names=None):
    suffix = generate_random_string()

    if names is None:
        names = [create_localized_text("name{0}".format(suffix))]

    concept = Concept(
        mnemonic='concept{0}'.format(suffix),
        updated_by=user,
        parent=source,
        concept_class='First',
        names=names,
        descriptions=[create_localized_text("desc{0}".format(suffix))]
    )

    kwargs = {
        'parent_resource': source,
    }

    Concept.persist_new(concept, user, **kwargs)

    return Concept.objects.get(id=concept.id)


def create_mapping(user, source, from_concept, to_concept, map_type="Same As"):
    mapping = Mapping(
        created_by=user,
        updated_by=user,
        parent=source,
        map_type=map_type,
        from_concept=from_concept,
        to_concept=to_concept,
        public_access=ACCESS_TYPE_VIEW,
    )

    kwargs = {
        'parent_resource': source,
    }

    Mapping.persist_new(mapping, user, **kwargs)

    return Mapping.objects.get(id=mapping.id)