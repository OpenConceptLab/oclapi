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
    def setUp(self):
        user = create_user()
        org_ocl = create_organization("OCL")
        create_lookup_concept_classes(user, org_ocl)

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


def create_localized_text(name, locale='en', type='FULLY_SPECIFIED', locale_preferred=False):
    return LocalizedText(name=name, locale=locale, type=type, locale_preferred=locale_preferred)


def create_user():
    suffix = generate_random_string()

    user = User.objects.create(
        username="test{0}".format(suffix),
        password="test{0}".format(suffix),
        email='user{0}@test.com'.format(suffix),
        first_name='Test',
        last_name='User'
    )
    create_user_profile(user)

    return user


def create_user_profile(user):
    suffix = generate_random_string()
    mnemonic = user.username if user else 'user{0}'.format(suffix)
    return UserProfile.objects.create(user=user, mnemonic=mnemonic)


def create_organization(name=None, mnemonic=None):
    suffix = generate_random_string()
    name = name if name else 'org{0}'.format(suffix)
    mnemonic = mnemonic if mnemonic else name
    return Organization.objects.create(name=name, mnemonic=mnemonic)


def create_source(user, validation_schema=None, organization=None, name=None):
    suffix = generate_random_string()

    source = Source(
        name=name if name else "source{0}".format(suffix),
        mnemonic=name if name else "source{0}".format(suffix),
        full_name=name if name else "Source {0}".format(suffix),
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


def create_collection(user, validation_schema=None, name=None):
    suffix = generate_random_string()

    collection = Collection(
        name=name if name else "collection{0}".format(suffix),
        mnemonic=name if name else "collection{0}".format(suffix),
        full_name=name if name else "Collection {0}".format(suffix),
        collection_type='Dictionary',
        public_access=ACCESS_TYPE_EDIT,
        default_locale='en',
        supported_locales=['en'],
        website='www.collection2.com',
        description='This is the second test collection',
        custom_validation_schema=validation_schema
    )

    kwargs = {
        'parent_resource': UserProfile.objects.get(user=user)
    }

    Collection.persist_new(collection, user, **kwargs)

    return Collection.objects.get(id=collection.id)


def create_concept(user, source, names=None, mnemonic=None, descriptions=None, concept_class=None, datatype=None,
                   force=False):
    suffix = generate_random_string()

    if not names and not force:
        names = [create_localized_text("name{0}".format(suffix))]

    if not mnemonic and not force:
        mnemonic = 'concept{0}'.format(suffix)

    if not descriptions and not force:
        descriptions = [create_localized_text("desc{0}".format(suffix))]

    concept = Concept(
        mnemonic=mnemonic,
        updated_by=user,
        datatype=datatype if datatype else "None",
        concept_class=concept_class if concept_class else 'Diagnosis',
        names=names,
        descriptions=descriptions,
    )

    if source is not None:
        kwargs = {
            'parent_resource': source,
        }
        errors = Concept.persist_new(concept, user, **kwargs)
    else:
        errors = Concept.persist_new(concept, user)

    return concept, errors


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


def create_lookup_concept_classes(user, org_ocl):
    classes_source = create_source(user, organization=org_ocl, name="Classes")
    datatypes_source = create_source(user, organization=org_ocl, name="Datatypes")
    nametypes_source = create_source(user, organization=org_ocl, name="NameTypes")
    descriptiontypes_source = create_source(user, organization=org_ocl, name="DescriptionTypes")
    maptypes_source = create_source(user, organization=org_ocl, name="MapTypes")
    locales_source = create_source(user, organization=org_ocl, name="Locales")

    create_concept(user, classes_source, concept_class="Concept Class", names=[create_localized_text("Diagnosis")])
    create_concept(user, classes_source, concept_class="Concept Class", names=[create_localized_text("Drug")])

    create_concept(user, datatypes_source, concept_class="Datatype",
                   names=[create_localized_text("None"), create_localized_text("N/A")])

    create_concept(user, nametypes_source, concept_class="NameType",
                   names=[create_localized_text("FULLY_SPECIFIED"), create_localized_text("Fully Specified")])
    create_concept(user, nametypes_source, concept_class="NameType",
                   names=[create_localized_text("Short"), create_localized_text("SHORT")])
    create_concept(user, nametypes_source, concept_class="NameType",
                   names=[create_localized_text("INDEX_TERM"), create_localized_text("Index Term")])
    create_concept(user, nametypes_source, concept_class="NameType", names=[create_localized_text("None")])

    create_concept(user, descriptiontypes_source, concept_class="DescriptionType",
                   names=[create_localized_text("None")])
    create_concept(user, descriptiontypes_source, concept_class="DescriptionType",
                   names=[create_localized_text("FULLY_SPECIFIED")])

    create_concept(user, maptypes_source, concept_class="MapType",
                   names=[create_localized_text("SAME-AS"), create_localized_text("Same As")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("Is Subset of")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("Different")])
    create_concept(user, maptypes_source, concept_class="MapType",
                   names=[create_localized_text("BROADER-THAN"), create_localized_text("Broader Than"),
                          create_localized_text("BROADER_THAN")])
    create_concept(user, maptypes_source, concept_class="MapType",
                   names=[create_localized_text("NARROWER-THAN"), create_localized_text("Narrower Than"),
                          create_localized_text("NARROWER_THAN")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("Q-AND-A")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("More specific than")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("Less specific than")])
    create_concept(user, maptypes_source, concept_class="MapType", names=[create_localized_text("Something Else")])

    create_concept(user, locales_source, concept_class="Locale", names=[create_localized_text("en")])
    create_concept(user, locales_source, concept_class="Locale", names=[create_localized_text("es")])
    create_concept(user, locales_source, concept_class="Locale", names=[create_localized_text("fr")])
    create_concept(user, locales_source, concept_class="Locale", names=[create_localized_text("tr")])
