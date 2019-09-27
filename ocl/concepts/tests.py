"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import logging
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from concepts.validation_messages import OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE, \
    OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE, OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE, \
    OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE, OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME, \
    OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED, OPENMRS_DESCRIPTION_LOCALE, OPENMRS_NAME_LOCALE, OPENMRS_DESCRIPTION_TYPE, \
    OPENMRS_NAME_TYPE, OPENMRS_DATATYPE, OPENMRS_CONCEPT_CLASS, BASIC_DESCRIPTION_CANNOT_BE_EMPTY, \
    OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE, OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME
from concepts.validators import ValidatorSpecifier
from concepts.views import ConceptVersionListView
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
from test_helper.base import *

logger = logging.getLogger('oclapi')

class ConceptBaseTest(OclApiBaseTestCase):
    def setUp(self):
        super(ConceptBaseTest, self).setUp()
        self.user1 = User.objects.create(
            username='user1',
            email='user1@test.com',
            last_name='One',
            first_name='User'
        )
        self.user1.set_password('user1')
        self.user1.save()
        self.user2 = User.objects.create(
            username='user2',
            email='user2@test.com',
            last_name='Two',
            first_name='User'
        )
        self.user2.set_password('user2')
        self.user2.save()

        self.userprofile1 = UserProfile.objects.create(user=self.user1, mnemonic='user1')
        self.userprofile2 = UserProfile.objects.create(user=self.user2, mnemonic='user2')

        self.org1 = Organization.objects.create(name='org1', mnemonic='org1', members=[self.user1.id])
        self.org2 = Organization.objects.create(name='org2', mnemonic='org2', members=[self.user2.id])

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
            custom_validation_schema=None
        )
        kwargs = {
            'parent_resource': self.org1
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
            custom_validation_schema=None
        )
        kwargs = {
            'parent_resource': self.org2,
        }
        Source.persist_new(self.source2, self.user2, **kwargs)
        self.source2 = Source.objects.get(id=self.source2.id)

        self.source_for_openmrs = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS,
                                                organization=self.org1)

        self.name = create_localized_text(name='Fred', locale='es', type='FULLY_SPECIFIED')
        self.description = create_localized_text(name='guapo', locale='es')


class ConceptTest(ConceptBaseTest):
    def test_create_concept_positive(self):
        (concept, errors) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=self.source1,
            names=[self.name]
        )

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)

    def test_create_concept_positive__mnemonic_with_underscore(self):
        (concept, errors) = create_concept(
            mnemonic='concept_1',
            user=self.user1,
            source=self.source1,
            names=[self.name]
        )

        self.assertTrue(Concept.objects.filter(mnemonic='concept_1').exists())

    def test_create_concept_positive__extras_with_period_in_name(self):
        (concept, errors) = create_concept(
            mnemonic='extras-concept1',
            user=self.user1,
            source=self.source1,
            names=[self.name],
            extras={"This.should.work": "Attribute with periods in key"}
        )

        concept = Concept.objects.get(mnemonic='extras-concept1')

        self.assertTrue(Concept.objects.filter(mnemonic='extras-concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(1, concept.num_versions)
        self.assertEquals({"This.should.work": "Attribute with periods in key"}, concept.extras)

    def test_create_concept_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                concept_class='Diagnosis',
                names=[self.name],
                descriptions=[self.name],
                datatype="None"
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_owner(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                parent=self.source1,
                updated_by=self.user1,
                concept_class='Diagnosis',
                names=[self.name],
                descriptions=[self.name],
                datatype="None"
            )
            concept.full_clean()
            concept.save()

    def test_create_concept_negative__no_class(self):
        with self.assertRaises(ValidationError):
            concept = Concept(
                mnemonic='concept1',
                created_by=self.user1,
                updated_by=self.user1,
                parent=self.source1,
                names=[self.name],
                descriptions=[self.name],
                datatype="None"
            )
            concept.full_clean()
            concept.save()

    def test_concept_display_name(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Diagnosis',
            names=[self.name],
            descriptions=[self.name],
            datatype="None"
        )
        display_name = LocalizedText(
            name='concept1',
            locale='en',
            locale_preferred=True,
            type='FULLY_SPECIFIED'
        )
        concept.names.append(display_name)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name.name, concept.display_name)
        self.assertEquals(display_name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_concept_display_name_preferred(self):
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            concept_class='Diagnosis',
            descriptions=[self.name],
            datatype="None"
        )
        display_name1 = LocalizedText(
            name='concept1',
            locale='en',
            locale_preferred=True,
            type='FULLY_SPECIFIED'
        )
        concept.names.append(display_name1)
        display_name2 = LocalizedText(
            name='le concept1',
            locale='fr',
            type='FULLY_SPECIFIED'
        )
        concept.names.append(display_name2)
        concept.full_clean()
        concept.save()

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(display_name1.name, concept.display_name)
        self.assertEquals(display_name1.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(0, concept.num_versions)

    def test_concept_access_changes_with_source(self):
        public_access = self.source1.public_access
        concept = Concept(
            mnemonic='concept1',
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            public_access=public_access,
            concept_class='Diagnosis',
            names=[self.name],
            descriptions=[self.name],
            datatype="None"
        )
        concept.full_clean()
        concept.save()

        self.assertEquals(self.source1.public_access, concept.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

        concept = Concept.objects.get(id=concept.id)
        self.assertNotEquals(public_access, self.source1.public_access)
        self.assertEquals(self.source1.public_access, concept.public_access)

    def test_get_latest_version(self):
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

        (concept1, errors) = create_concept(mnemonic='concept12', user=self.user1, source=source)

        concept = Concept.objects.get(mnemonic=concept1.mnemonic)
        concept_version1 = ConceptVersion.objects.get(versioned_object_id=concept.id)
        self.assertEquals(concept.get_latest_version.id, concept_version1.id)


class OpenMrsLookupValueValidationTest(ConceptBaseTest):
    def test_concept_class_is_valid_attribute_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='XYZQWERT',
                                           source=source,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['concept_class'][0], OPENMRS_CONCEPT_CLASS)

    def test_data_type_is_valid_attribute_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=source,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')], datatype='XYZWERRTR')

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['data_type'][0], OPENMRS_DATATYPE)

    def test_description_type_is_valid_attribute_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=source,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[create_localized_text(name='Grip Description', locale='es',
                                                                               locale_preferred=True,
                                                                               type='XYZWERRTR')])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['descriptions'][0], OPENMRS_DESCRIPTION_TYPE)

    def test_name_locale_is_valid_attribute_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=source,
                                           names=[create_localized_text(name='Grip', locale='XWERTY',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[
                                               create_localized_text(name='Grip Description', locale='English',
                                                                     locale_preferred=True,
                                                                     type='FULLY_SPECIFIED')])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0], OPENMRS_NAME_LOCALE)

    def test_description_locale_is_valid_attribute_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=source,
                                           names=[create_localized_text(name='Grip', locale='English',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[
                                               create_localized_text(name='Grip Description', locale='XWERTY',
                                                                     locale_preferred=True,
                                                                     type='FULLY_SPECIFIED')])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['descriptions'][0], OPENMRS_DESCRIPTION_LOCALE)


class ConceptBasicValidationTest(ConceptBaseTest):
    def test_concept_class_is_valid_attribute_positive(self):
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Drug',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='es', locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')])

        self.assertEquals(0, len(errors))

    def test_data_type_is_valid_attribute_positive(self):
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')], datatype='Text')

        self.assertEquals(0, len(errors))

    def test_name_type_is_valid_attribute_positive(self):
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='Short'),
                                                  create_localized_text(name='Nezle', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')])

        self.assertEquals(0, len(errors))

    def test_description_type_is_valid_attribute_positive(self):

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='es',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[
                                               create_localized_text(name='Grip Description', locale='es',
                                                                     locale_preferred=True,
                                                                     type='Definition')])

        self.assertEquals(0, len(errors))

    def test_name_locale_is_valid_attribute_positive(self):
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='Abkhazian',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[
                                               create_localized_text(name='Grip Description', locale='English',
                                                                     locale_preferred=True,
                                                                     type='FULLY_SPECIFIED')])

        self.assertEquals(0, len(errors))

    def test_description_locale_is_valid_attribute_positive(self):
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, concept_class='Diagnosis',
                                           source=self.source1,
                                           names=[create_localized_text(name='Grip', locale='English',
                                                                        locale_preferred=True,
                                                                        type='FULLY_SPECIFIED')],
                                           descriptions=[
                                               create_localized_text(name='Grip Description', locale='Abkhazian',
                                                                     locale_preferred=True,
                                                                     type='FULLY_SPECIFIED')])

        self.assertEquals(0, len(errors))

    def test_unique_preferred_name_per_source_positive(self):
        (concept1, errors1) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Concept Unique Preferred Name 1', locale_preferred=True, type='FULLY_SPECIFIED')
        ])
        (concept2, errors2) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Concept Unique Preferred Name 2', locale_preferred=True, type='FULLY_SPECIFIED')
        ])

        self.assertEquals(0, len(errors1))
        self.assertEquals(0, len(errors2))

    def test_duplicate_preferred_name_per_source_should_pass_if_not_preferred(self):
        (concept1, errors1) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale_preferred=True,
                                  type='FULLY_SPECIFIED')
        ])
        (concept2, errors2) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale_preferred=False,
                                  type='FULLY_SPECIFIED')
        ])

        self.assertEquals(0, len(errors1))
        self.assertEquals(0, len(errors2))

    def test_unique_preferred_name_per_locale_within_concept_positive(self):
        (concept, errors) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale='en',
                                  locale_preferred=True, type='FULLY_SPECIFIED'),
            create_localized_text(name='Concept Non Unique Preferred Name', locale='es',
                                  locale_preferred=True, type='FULLY_SPECIFIED'),
        ])

        self.assertEquals(0, len(errors))

    def test_preferred_name_uniqueness_when_name_exists_in_source_for_different_locale(self):
        (_, _) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Name 1', type='Fully Specified', locale_preferred=False, locale='fr'),
            create_localized_text(name='Name 2', type='Short', locale='en')
        ])

        (_, errors) = create_concept(user=self.user1, source=self.source1, names=[
            create_localized_text(name='Name 1', type='Fully Specified', locale_preferred=True, locale='en')
        ])

        self.assertEquals(0, len(errors))

    def test_null_description_should_pass(self):
        (_, errors) = create_concept(mnemonic="conceptNoDescription", user=self.user1, source=self.source1,
                                     descriptions=None, force=True, names=[
                create_localized_text(name='Name 1', type='Fully Specified', locale_preferred=True, locale='en')
            ])

        self.assertEquals(0, len(errors))

    def test_empty_descriptions_array_should_pass(self):
        (_, errors) = create_concept(user=self.user1, source=self.source1, descriptions=[])

        self.assertEquals(0, len(errors))

    def test_empty_description_field_should_fail(self):
        (_, errors) = create_concept(user=self.user1, source=self.source1, descriptions=[
            create_localized_text(name=None, locale='en', type="None"),
            create_localized_text(name="description", locale='en', type="None")
        ])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['descriptions'][0], BASIC_DESCRIPTION_CANNOT_BE_EMPTY)


class ConceptClassMethodsTest(ConceptBaseTest):
    def test_persist_new_positive(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1, names=[self.name])

        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.get_concept_ids()))
        self.assertTrue(concept_version.id in source_version.get_concept_ids())
        self.assertEquals(concept_version.mnemonic, concept_version.id)

    def test_persist_new_negative__no_owner(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=None, source=self.source1)

        self.assertEquals(1, len(errors))
        self.assertTrue('created_by' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.get_concept_ids()))

    def test_persist_new_negative__no_parent(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=None)

        self.assertEquals(1, len(errors))
        self.assertTrue('parent' in errors)

        self.assertFalse(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(0, len(source_version.get_concept_ids()))

    def test_persist_new_negative_repeated_mnemonic(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1, names=[self.name])

        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.get_concept_ids()))
        self.assertTrue(concept_version.id in source_version.get_concept_ids())

        # Repeat with same mnemonic
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1)

        self.assertEquals(1, len(errors))
        self.assertTrue('__all__' in errors)
        self.assertEquals(0, concept.num_versions)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.get_concept_ids()))

    def test_persist_new_positive__repeated_mnemonic(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1, names=[self.name])

        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.get_concept_ids()))
        self.assertTrue(concept_version.id in source_version.get_concept_ids())

        # Repeat with same mnemonic, different parent
        source_version = SourceVersion.get_latest_version_of(self.source2)
        self.assertEquals(0, len(source_version.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source2, names=[self.name])

        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source2.parent_resource, concept.owner_name)
        self.assertEquals(self.source2.owner_type, concept.owner_type)
        self.assertEquals(self.source2.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        source_version = SourceVersion.objects.get(id=source_version.id)
        self.assertEquals(1, len(source_version.get_concept_ids()))
        self.assertTrue(concept_version.id in source_version.get_concept_ids())

    def test_persist_new_positive__earlier_source_version(self):
        version1 = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(version1.get_concept_ids()))
        version2 = SourceVersion.for_base_object(self.source1, label='version2')
        version2.save()
        self.assertEquals(0, len(version2.get_concept_ids()))

        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1, names=[self.name])

        self.assertEquals(0, len(errors))

        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(self.name.name, concept.display_name)
        self.assertEquals(self.name.locale, concept.display_locale)
        self.assertEquals(self.source1.owner_name, concept.owner_name)
        self.assertEquals(self.source1.owner_type, concept.owner_type)
        self.assertEquals(self.source1.public_access, concept.public_access)
        self.assertEquals(1, concept.num_versions)
        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertEquals(concept_version, concept_version.root_version)

        version1 = SourceVersion.objects.get(id=version1.id)
        self.assertEquals(1, len(version1.get_concept_ids()))
        self.assertTrue(concept_version.id in version1.get_concept_ids())

        version2 = SourceVersion.objects.get(id=version2.id)
        self.assertEquals(0, len(version2.get_concept_ids()))
        self.assertFalse(concept_version.id in version2.get_concept_ids())

    def test_retire_positive(self):
        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertEquals(0, len(source_version.get_concept_ids()))
        (concept, errors) = create_concept(mnemonic='concept1', user=self.user1, source=self.source1)

        self.assertEquals(0, len(errors))
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertFalse(concept.retired)
        self.assertEquals(1, concept.num_versions)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(concept_version.is_latest_version)
        self.assertFalse(concept_version.retired)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertItemsEqual([concept_version.id], source_version.get_concept_ids())

        errors = Concept.retire(concept, self.user1)
        self.assertFalse(errors)
        self.assertTrue(Concept.objects.filter(mnemonic='concept1').exists())
        self.assertTrue(concept.retired)
        self.assertEquals(2, concept.num_versions)

        previous_version = ConceptVersion.objects.get(id=concept_version.id)
        self.assertFalse(previous_version.is_latest_version)
        self.assertFalse(previous_version.retired)

        concept_version = ConceptVersion.get_latest_version_of(concept)
        self.assertTrue(concept_version.is_latest_version)
        self.assertTrue(concept_version.retired)
        self.assertEquals(self.user1.username, concept_version.version_created_by)

        source_version = SourceVersion.get_latest_version_of(self.source1)
        self.assertItemsEqual([concept_version.id], source_version.get_concept_ids())

        self.assertEquals(
            1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=True).count())
        self.assertEquals(
            1, ConceptVersion.objects.filter(versioned_object_id=concept.id, retired=False).count())

        errors = Concept.retire(concept, self.user1)
        self.assertEquals(1, len(errors))


class ConceptVersionTest(ConceptBaseTest):
    def setUp(self):
        super(ConceptVersionTest, self).setUp()

        display_name = LocalizedText(
            name='concept1',
            locale='en',
            type='FULLY_SPECIFIED'
        )
        (self.concept1, errors) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=self.source1,
            names=[self.name, display_name]
        )
        (self.concept2, errors) = create_concept(
            mnemonic='concept1',
            user=self.user1,
            source=self.source1,
            names=[self.name]
        )

    def test_create_concept_version_positive(self):
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='Diagnosis',
            datatype=self.concept1.datatype,
            names=self.concept1.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")]
        )
        concept_version.full_clean()
        concept_version.save()
        self.assertTrue(ConceptVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            versioned_object_id=self.concept1.id,
        ).exists())
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        self.assertEquals(self.concept1.mnemonic, concept_version.name)
        self.assertEquals(self.concept1.owner_name, concept_version.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_version.owner_type)
        self.assertEquals(self.concept1.display_name, concept_version.display_name)
        self.assertEquals(self.concept1.display_locale, concept_version.display_locale)

    def test_create_concept_version_negative__no_mnemonic(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                versioned_object=self.concept1,
                concept_class='Diagnosis',
                datatype=self.concept1.datatype,
                names=[self.name],
                descriptions=[self.name]
            )
            concept_version.full_clean()
            concept_version.save()

    def test_create_concept_version_negative__no_concept_class(self):
        with self.assertRaises(ValidationError):
            concept_version = ConceptVersion(
                mnemonic='version1',
                versioned_object=self.concept1,
                datatype=self.concept1.datatype,
                names=[self.name],
                descriptions=[self.name]
            )
            concept_version.full_clean()
            concept_version.save()

    def test_concept_version_clone(self):
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='Diagnosis',
            datatype=self.concept1.datatype,
            names=self.concept1.names,
            descriptions=[self.name],
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
        )
        concept_version.full_clean()
        concept_version.save()
        self.assertTrue(ConceptVersion.objects.filter(
            mnemonic='version1',
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            versioned_object_id=self.concept1.id,
        ).exists())
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        self.assertEquals(self.concept1.mnemonic, concept_version.name)
        self.assertEquals(self.concept1.owner_name, concept_version.owner_name)
        self.assertEquals(self.concept1.owner_type, concept_version.owner_type)
        self.assertEquals(self.concept1.display_name, concept_version.display_name)
        self.assertEquals(self.concept1.display_locale, concept_version.display_locale)

        version2 = concept_version.clone()
        version2.mnemonic = 'version2'
        version2.created_by = self.user1.username
        version2.updated_by = self.user1.username
        version2.version_created_by = self.user1.username
        version2.full_clean()
        version2.save()

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(concept_version, version2.previous_version)
        self.assertEquals(concept_version.public_access, version2.public_access)

        self.assertEquals(self.concept1, version2.versioned_object)
        self.assertEquals(self.concept1.mnemonic, version2.name)
        self.assertEquals(self.concept1.owner_name, version2.owner_name)
        self.assertEquals(self.concept1.owner_type, version2.owner_type)
        self.assertEquals(self.concept1.display_name, version2.display_name)
        self.assertEquals(self.concept1.display_locale, version2.display_locale)

    def test_concept_version_inherits_public_access__positive(self):
        public_access = self.source1.public_access
        self.assertEquals(1, self.concept1.num_versions)
        concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='Diagnosis',
            datatype=self.concept1.datatype,
            public_access=public_access,
            names=self.concept1.names,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")]
        )
        concept_version.full_clean()
        concept_version.save()

        self.assertEquals(self.source1.public_access, concept_version.public_access)
        self.source1.public_access = ACCESS_TYPE_VIEW
        self.source1.save()

        self.assertNotEquals(public_access, self.source1.public_access)
        concept_version = ConceptVersion.objects.get(id=concept_version.id)
        self.assertEquals(self.source1.public_access, concept_version.public_access)

    def test_concept_version_all_names(self):
        concept_version = ConceptVersion.objects.get(versioned_object_id=self.concept1.id)
        expected_names_list = ['concept1', 'Fred']
        self.assertItemsEqual(concept_version.all_names, expected_names_list)

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

        (concept1, errors) = create_concept(mnemonic="concept12", user=self.user1, source=source)
        (another_concept, errors) = create_concept(mnemonic="anotherConcept", user=self.user1, source=source)

        another_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=another_concept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=concept1.mnemonic).mnemonic + '/'

        references = [concept1_reference, another_concept_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion.objects.get(
            versioned_object_id=Concept.objects.get(mnemonic=concept1.mnemonic).id)

        self.assertEquals(concept_version.get_collection_ids(), [Collection.objects.get(mnemonic=collection.mnemonic).id])

    def test_collections_ids_with_latest_concept_version(self):
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

        (concept1, errors) = create_concept(mnemonic='concept12', user=self.user1, source=source)

        initial_concept_version = ConceptVersion.objects.get(versioned_object_id=concept1.id)
        ConceptVersion.persist_clone(initial_concept_version.clone(), self.user1)
        new_concept_version = ConceptVersion.objects.filter(versioned_object_id=concept1.id).order_by('-created_at')[0]

        collection.expressions = [new_concept_version.uri]
        collection.full_clean()
        collection.save()

        self.assertEquals(initial_concept_version.get_collection_ids(), [])
        self.assertEquals(new_concept_version.get_collection_ids(), [Collection.objects.get(mnemonic=collection.mnemonic).id])

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

        (concept1, errors) = create_concept(mnemonic='concept12', user=self.user1, source=source)

        (another_concept, errors) = create_concept(mnemonic='anotherConcept', user=self.user1, source=source)

        another_concept_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=another_concept.mnemonic).mnemonic + '/'
        concept1_reference = '/orgs/org1/sources/source/concepts/' + Concept.objects.get(
            mnemonic=concept1.mnemonic).mnemonic + '/'

        references = [concept1_reference, another_concept_reference]

        collection.expressions = references
        collection.full_clean()
        collection.save()

        concept_version = ConceptVersion.objects.get(
            versioned_object_id=Concept.objects.get(mnemonic=another_concept.mnemonic).id)

        version = CollectionVersion.for_base_object(collection, 'version1')
        kwargs = {}
        CollectionVersion.persist_new(version, **kwargs)

        self.assertEquals(len(concept_version.get_collection_version_ids()), 2)
        self.assertEquals(concept_version.get_collection_version_ids()[1],
                          CollectionVersion.objects.get(mnemonic='version1').id)


class ConceptVersionStaticMethodsTest(ConceptBaseTest):
    def setUp(self):
        super(ConceptVersionStaticMethodsTest, self).setUp()
        self.concept1 = Concept(mnemonic='concept1', concept_class='Diagnosis', public_access=ACCESS_TYPE_EDIT,
                                datatype="None",
                                descriptions=[create_localized_text("aDescription")])
        display_name = LocalizedText(name='concept1', locale='en', type='FULLY_SPECIFIED')

        self.concept1.names.append(display_name)
        kwargs = {
            'parent_resource': self.source1,
        }
        errors = Concept.persist_new(self.concept1, self.user1, **kwargs)

        initial_version = ConceptVersion.get_latest_version_of(self.concept1)

        self.concept2 = Concept(mnemonic='concept2', concept_class='Drug', names=[self.name],
                                descriptions=[create_localized_text("aDescription")])
        kwargs = {
            'parent_resource': self.source2,
        }
        Concept.persist_new(self.concept2, self.user1, **kwargs)

        self.concept_version = ConceptVersion(
            mnemonic='version1',
            versioned_object=self.concept1,
            concept_class='Diagnosis',
            datatype=self.concept1.datatype,
            names=self.concept1.names,
            previous_version=initial_version,
            created_by=self.user1.username,
            updated_by=self.user1.username,
            version_created_by=self.user1.username,
            descriptions=[create_localized_text("aDescription")]
        )
        self.concept_version.full_clean()
        self.concept_version.save()

    def test_for_concept_positive(self):
        self.concept1.datatype = 'Boolean'
        self.concept1.save()

        label = 'version1'
        version = ConceptVersion.for_concept(self.concept1, label)

        self.assertEquals(label, version.mnemonic)
        self.assertEquals(self.concept1, version.versioned_object)
        self.assertEquals(self.concept1.concept_class, version.concept_class)
        self.assertEquals(self.concept1.datatype, version.datatype)
        self.assertEquals(self.concept1.names, version.names)
        self.assertEquals(self.concept1.descriptions, version.descriptions)
        self.assertEquals(self.concept1.retired, version.retired)
        self.assertEquals(self.concept1.public_access, version.public_access)
        self.assertEquals(self.concept1.external_id, version.external_id)
        self.assertFalse(version.released)

    def test_persist_clone_positive(self):
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        source_version = SourceVersion.get_latest_version_of(self.source1)

        source_version.update_concept_version(self.concept_version)
        self.assertItemsEqual([self.concept_version.id], source_version.get_concept_ids())

        version2 = self.concept_version.clone()
        errors = ConceptVersion.persist_clone(version2, self.user1)
        self.assertEquals(0, len(errors))

        self.assertEquals(3, self.concept1.num_versions)
        self.assertEquals(version2, ConceptVersion.get_latest_version_of(self.concept1))
        self.assertEquals(self.concept_version.public_access, version2.public_access)
        self.assertEquals(self.concept_version, version2.previous_version)
        self.assertEquals(self.concept_version.root_version, version2.root_version)
        self.assertEquals(self.concept_version.external_id, version2.external_id)
        self.assertEquals(self.user1.username, version2.version_created_by)

        self.assertItemsEqual([version2.id], source_version.get_concept_ids())

    def test_persist_clone_negative__no_user(self):
        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))

        source_version = SourceVersion.get_latest_version_of(self.source1)

        source_version.update_concept_version(self.concept_version)
        self.assertItemsEqual([self.concept_version.id], source_version.get_concept_ids())

        version2 = self.concept_version.clone()
        errors = ConceptVersion.persist_clone(version2)
        self.assertEquals(1, len(errors))
        self.assertTrue('version_created_by' in errors)

        self.assertEquals(2, self.concept1.num_versions)
        self.assertEquals(
            self.concept_version, ConceptVersion.get_latest_version_of(self.concept1))


class ConceptVersionListViewTest(ConceptBaseTest):
    def test_get_csv_rows(self):
        display_name = LocalizedText(name='concept1', locale='en', type='FULLY_SPECIFIED')

        (concept, _) = create_concept(
            mnemonic='concept1',
            source=self.source1,
            user=self.user1,
            names=[display_name],
            descriptions=[display_name]
        )

        concept_version = concept.get_latest_version

        view = ConceptVersionListView()
        view.kwargs = {}
        view.parent_resource_version = self.source1.get_head()
        csv_rows = view.get_csv_rows()
        self.assertEquals(len(csv_rows), 1)
        self.assertEquals(csv_rows[0].get('Retired'), False)
        self.assertEquals(csv_rows[0].get('Datatype'), "None")
        self.assertEquals(csv_rows[0].get('Concept ID'), concept.mnemonic)
        self.assertEquals(csv_rows[0].get('External ID'), None)
        self.assertEquals(csv_rows[0].get('URI'), concept_version.uri)
        self.assertEquals(csv_rows[0].get('Synonyms'), 'concept1 [FULLY_SPECIFIED] [en]')
        self.assertEquals(csv_rows[0].get('Attributes'), '')
        self.assertEquals(csv_rows[0].get('Mappings'), '')

    def test_get_csv_rows_with_attributes(self):
        display_name = LocalizedText(name='concept1', locale='en', type='FULLY_SPECIFIED')

        (concept, _) = create_concept(
            mnemonic='concept1',
            source=self.source1,
            user=self.user1,
            names=[display_name],
            descriptions=[display_name],
            extras={"attr1": "value1", "attr2": "value2"}
        )

        view = ConceptVersionListView()
        view.kwargs = {}
        view.parent_resource_version = self.source1.get_head()
        csv_rows = view.get_csv_rows()
        self.assertEquals(len(csv_rows), 1)
        self.assertEquals(csv_rows[0].get('Attributes'), 'attr2: value2; attr1: value1')

    def test_get_csv_rows_with_mappings(self):
        display_name_1 = LocalizedText(name='concept1', locale='en', type='FULLY_SPECIFIED')
        display_name_2 = LocalizedText(name='concept2', locale='en', type='FULLY_SPECIFIED')

        (concept1, _) = create_concept(
            mnemonic='concept1',
            source=self.source1,
            user=self.user1,
            names=[display_name_1],
            descriptions=[display_name_1]
        )

        (concept2, _) = create_concept(
            mnemonic='concept2',
            source=self.source2,
            user=self.user1,
            names=[display_name_2],
            descriptions=[display_name_2]
        )

        mapping1 = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='Same As',
            from_concept=concept1,
            to_concept=concept2,
            external_id='versionmapping1',
        )
        mapping1.full_clean()
        mapping1.save()

        mapping2 = Mapping(
            created_by=self.user1,
            updated_by=self.user1,
            parent=self.source1,
            map_type='NARROWER-THAN',
            from_concept=concept1,
            to_source=self.source1,
            to_concept_code='code',
            to_concept_name='name',
            external_id='versionmapping2',
        )
        mapping2.full_clean()
        mapping2.save()

        view = ConceptVersionListView()
        view.kwargs = {}
        view.parent_resource_version = self.source1.get_head()
        csv_rows = view.get_csv_rows()
        self.assertEquals(len(csv_rows), 1)
        self.assertEquals(csv_rows[0].get('Mappings'), 'org1 / source1 / concept1 : concept1 <Same As> org2 / source2 / concept2 : concept2 [Internal]; '
                                                       'org1 / source1 / concept1 : concept1 <NARROWER-THAN> org1 / source1 / code : name [External]')



class OpenMRSConceptValidationTest(ConceptBaseTest):
    def test_concept_should_have_exactly_one_preferred_name_per_locale(self):
        user = create_user()

        name_en1 = create_localized_text('PreferredName1', locale_preferred=True)
        name_en2 = create_localized_text('PreferredName2', locale_preferred=True)
        name_tr = create_localized_text('PreferredName3', locale="tr", locale_preferred=True)

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=user, source=source, names=[name_en1, name_en2, name_tr])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_MUST_HAVE_EXACTLY_ONE_PREFERRED_NAME + ': PreferredName2 (locale: en, preferred: yes)')

    def test_concepts_should_have_unique_fully_specified_name_per_locale(self):
        user = create_user()

        name_fully_specified1 = create_localized_text('FullySpecifiedName1')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept1, errors1) = create_concept(user=user, source=source, names=[name_fully_specified1])
        (concept2, errors2) = create_concept(user=user, source=source, names=[name_fully_specified1])

        self.assertEquals(0, len(errors1))

        self.assertEquals(errors2['names'][0],
                          OPENMRS_FULLY_SPECIFIED_NAME_UNIQUE_PER_SOURCE_LOCALE + ': FullySpecifiedName1 (locale: en, preferred: no)')

    def test_at_least_one_fully_specified_name_per_concept_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Fully Specified Name 1', locale='tr', type='Short'),
            create_localized_text(name='Fully Specified Name 2', locale='en', type='Short')
        ])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0], OPENMRS_AT_LEAST_ONE_FULLY_SPECIFIED_NAME)

    def test_duplicate_preferred_name_per_source_should_fail(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)
        (concept1, errors1) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale='en', locale_preferred=True,
                                  type='Fully Specified')
        ])

        short_and_preferred = create_localized_text(name='Concept Non Unique Preferred Name', locale='en',
                                                    locale_preferred=True,
                                                    type='None')
        fully_specified_but_not_preferred = create_localized_text(name='any name', locale='en', locale_preferred=False,
                                                                  type='Fully Specified')

        (concept2, errors2) = create_concept(user=self.user1, source=source, names=[
            short_and_preferred, fully_specified_but_not_preferred
        ])

        self.assertEquals(0, len(errors1))
        self.assertEquals(1, len(errors2))
        self.assertEquals(errors2['names'][0],
                          OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE + ': Concept Non Unique Preferred Name (locale: en, preferred: yes)')

    def test_unique_preferred_name_per_locale_within_concept_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale='es',
                                  locale_preferred=True, type='FULLY_SPECIFIED'),
            create_localized_text(name='Concept Non Unique Preferred Name', locale='es',
                                  locale_preferred=True, type='FULLY_SPECIFIED'),
        ])

        self.assertEquals(1, len(errors))

    def test_unique_preferred_name_per_locale_within_source_negative(self):
        source = create_source(self.user1, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept1, errors1) = create_concept(user=self.user1, source=source, names=[
            create_localized_text(name='Concept Non Unique Preferred Name', locale='en', locale_preferred=True,
                                  type='Fully Specified')
        ])

        short_and_preferred = create_localized_text(name='Concept Non Unique Preferred Name', locale='en',
                                                    locale_preferred=True,
                                                    type='None')
        fully_specified_but_not_preferred = create_localized_text(name='any name', locale='en', locale_preferred=False,
                                                                  type='Fully Specified')

        (concept2, errors2) = create_concept(user=self.user1, source=source, names=[
            short_and_preferred, fully_specified_but_not_preferred
        ])

        self.assertEquals(0, len(errors1))
        self.assertEquals(1, len(errors2))
        self.assertEquals(errors2['names'][0],
                          OPENMRS_PREFERRED_NAME_UNIQUE_PER_SOURCE_LOCALE + ': Concept Non Unique Preferred Name (locale: en, preferred: yes)')

    def test_a_preferred_name_can_not_be_a_short_name(self):
        user = create_user()

        short_name = create_localized_text("ShortName", locale_preferred=True, type="Short", locale='fr')

        name = create_localized_text('Fully Sepcified Name')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (_, errors) = create_concept(mnemonic='EOPN', source=source, user=user, names=[short_name, name])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED + ': ShortName (locale: fr, preferred: yes)')

    def test_a_preferred_name_can_not_be_an_index_search_term(self):
        user = create_user()

        name = create_localized_text("FullySpecifiedName")

        index_name = create_localized_text("IndexTermName", type="INDEX_TERM", locale_preferred=True, locale='tr')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (_, errors) = create_concept(mnemonic='EOPN', source=source, user=user, names=[name, index_name])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_SHORT_NAME_CANNOT_BE_PREFERRED + ': IndexTermName (locale: tr, preferred: yes)')

    def test_a_name_can_be_equal_to_a_short_name(self):
        user = create_user()

        name = create_localized_text("aName")

        short_name = create_localized_text("aName")
        short_name.type = "SHORT"

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=user, source=source, names=[short_name, name])

        self.assertEquals(0, len(errors))

    def test_a_name_should_be_unique(self):
        user = create_user()

        name = create_localized_text("aName")

        another_name = create_localized_text("aName")

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        (concept, errors) = create_concept(user=user, source=source, names=[name, another_name])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_NAMES_EXCEPT_SHORT_MUST_BE_UNIQUE)

    def test_only_one_fully_specified_name_per_locale(self):
        user = create_user()
        name1 = create_localized_text('fully specified 1', locale='en')
        name2 = create_localized_text('fully specified 2', locale='en')
        name3 = create_localized_text('fully specified 3', locale='fr')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        _, errors = create_concept(user=user, source=source, names=[name1, name2, name3])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_ONE_FULLY_SPECIFIED_NAME_PER_LOCALE + ': fully specified 2 (locale: en, preferred: no)')

    def test_no_more_than_one_short_name_per_locale(self):
        user = create_user()
        name1 = create_localized_text('fully specified 1', locale='en', type='Short')
        name2 = create_localized_text('fully specified 2', locale='en', type='Short')
        name3 = create_localized_text('fully specified 3', locale='fr')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        _, errors = create_concept(user=user, source=source, names=[name1, name2, name3])

        self.assertEquals(1, len(errors))
        self.assertEquals(errors['names'][0],
                          OPENMRS_NO_MORE_THAN_ONE_SHORT_NAME_PER_LOCALE + ': fully specified 2 (locale: en, preferred: no)')

    def test_locale_preferred_name_uniqueness_doesnt_apply_to_shorts(self):
        user = create_user()
        name_fully_specified_mg = create_localized_text('mg', locale='en', locale_preferred=True)
        name_short_mg = create_localized_text('mg', locale='en', type='Short')

        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        _, errors = create_concept(user, source, names=[name_fully_specified_mg, name_short_mg])

        self.assertEquals(0, len(errors))


class ValidatorSpecifierTest(ConceptBaseTest):
    def test_specifier_should_initialize_openmrs_validator_with_reference_values(self):
        user = create_user()
        source = create_source(user, validation_schema=CUSTOM_VALIDATION_SCHEMA_OPENMRS)

        expected_reference_values = {
            u'DescriptionTypes': [u'None', u'FULLY_SPECIFIED', u'Definition'],
            u'Datatypes': [u'None', u'N/A', u'Numeric', u'Coded', u'Text'],
            u'Classes': [u'Diagnosis', u'Drug', u'Test', u'Procedure'],
            u'Locales': [u'en', u'es', u'fr', u'tr', u'Abkhazian', u'English'],
            u'NameTypes': [u'FULLY_SPECIFIED', u'Fully Specified', u'Short', u'SHORT',
                           u'INDEX_TERM', u'Index Term', u'None']}

        validator = ValidatorSpecifier() \
            .with_validation_schema(CUSTOM_VALIDATION_SCHEMA_OPENMRS) \
            .with_repo(source) \
            .with_reference_values() \
            .get()

        actual_reference_values = validator.reference_values

        self.assertItemsEqual(expected_reference_values[u'DescriptionTypes'], actual_reference_values[u'DescriptionTypes'])
        self.assertItemsEqual(expected_reference_values[u'Datatypes'], actual_reference_values[u'Datatypes'])
        self.assertItemsEqual(expected_reference_values[u'Classes'], actual_reference_values[u'Classes'])
        self.assertItemsEqual(expected_reference_values[u'Locales'], actual_reference_values[u'Locales'])
        self.assertItemsEqual(expected_reference_values[u'NameTypes'], actual_reference_values[u'NameTypes'])
