from django.core.exceptions import ValidationError

from concepts.custom_validators import OpenMRSConceptValidator
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS, LOOKUP_CONCEPT_CLASSES
from sources.models import Source

__author__ = 'misternando'


class DictionaryItemMixin(object):
    @classmethod
    def create_initial_version(cls, obj, **kwargs):
        return None

    @classmethod
    def persist_new(cls, obj, created_by, **kwargs):
        errors = dict()
        user = created_by
        if not user:
            errors['created_by'] = 'Concept creator cannot be null.'
        parent_resource = kwargs.pop('parent_resource', None)
        if not parent_resource:
            errors['parent'] = 'Concept parent cannot be null.'
        if errors:
            return errors
        obj.created_by = user
        obj.updated_by = user
        obj.parent = parent_resource
        obj.public_access = parent_resource.public_access
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
        if errors:
            return errors

        parent_resource_version = kwargs.pop('parent_resource_version', None)
        if parent_resource_version is None:
            version_model = parent_resource.get_version_model()

            if version_model.__name__ in ['SourceVersion', 'CollectionVersion']:
                parent_resource_version = version_model.get_head_of(parent_resource)
            else:
                parent_resource_version = version_model.get_latest_version_of(parent_resource)

        child_list_attribute = kwargs.pop('child_list_attribute', 'concepts')

        initial_parent_children = getattr(parent_resource_version, child_list_attribute) or []
        initial_version = None
        errored_action = 'saving concept'
        persisted = False
        try:
            obj.save(**kwargs)

            # Create the initial version
            errored_action = 'creating initial version of dictionary item'
            initial_version = cls.create_initial_version(obj)

            # Associate the version with a version of the parent
            errored_action = 'associating dictionary item with parent resource'
            parent_children = getattr(parent_resource_version, child_list_attribute) or []
            child_id = initial_version.id if initial_version else obj.id
            parent_children.append(child_id)
            setattr(parent_resource_version, child_list_attribute, parent_children)
            parent_resource_version.save()

            # Save the initial version again to trigger the Solr update
            if initial_version is not None:
                initial_version.save()

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
                setattr(parent_resource_version, child_list_attribute, initial_parent_children)
                parent_resource_version.save()
                if initial_version:
                    initial_version.delete()
                if obj.id:
                    obj.delete()
        return errors


class ConceptValidationMixin:
    def clean(self):
        if not self.concept_class in LOOKUP_CONCEPT_CLASSES:
            self._lookup_attributes_should_be_valid()

        self._requires_at_least_one_description()
        self._requires_at_least_one_fully_specified_name()
        self._preferred_name_should_be_unique_for_source_and_locale()

        if self.parent_source.custom_validation_schema == CUSTOM_VALIDATION_SCHEMA_OPENMRS:
            custom_validator = OpenMRSConceptValidator(self)
            custom_validator.validate()

    def _preferred_name_should_be_unique_for_source_and_locale(self):
        from concepts.models import Concept, ConceptVersion

        # Concept preferred_name should be unique for same source and locale.
        validation_error = {'names': ['Concept preferred name must be unique for same source and locale']}
        preferred_names_in_concept = dict()
        self_id = getattr(self, "versioned_object_id", None)

        for name in [n for n in self.names if n.locale_preferred]:
            # making sure names in the submitted concept meet the same rule
            name_key = name.locale + name.name
            if preferred_names_in_concept.has_key(name_key):
                raise ValidationError(validation_error)

            preferred_names_in_concept[name_key] = True

            other_concepts_in_source = list(Concept.objects\
                .filter(parent_id=self.parent_source.id, is_active=True,retired=False)\
                .exclude(id=self_id)\
                .values_list('id', flat=True))

            if len(other_concepts_in_source) < 1:
                continue

            same_name_and_locale = {'versioned_object_id': {'$in': other_concepts_in_source},
                         'names': {'$elemMatch': {'name': name.name, 'locale': name.locale}},
                         'is_latest_version': True}

            if ConceptVersion.objects.raw_query(same_name_and_locale).count() > 0:
                raise ValidationError(validation_error)

    def _requires_at_least_one_fully_specified_name(self):
        # Concept requires at least one fully specified name
        fully_specified_name_count = len(
            filter(lambda n: n.is_fully_specified, self.names))
        if fully_specified_name_count < 1:
            raise ValidationError({'names': ['Concept requires at least one fully specified name']})

    def _requires_at_least_one_description(self):
        if (not self.descriptions) or len(self.descriptions) < 1:
            raise ValidationError({'names': ['Concept requires at least one description']})

    def _lookup_attributes_should_be_valid(self):
        from orgs.models import Organization
        ocl_org_filter = Organization.objects.filter(mnemonic='OCL')

        if ocl_org_filter.count() < 1:
            raise ValidationError({'names': ['Lookup attributes must be imported']})

        org = ocl_org_filter.get()

        self._concept_class_should_be_valid_attribute(org)
        self._data_type_should_be_valid_attribute(org)
        self._name_type_should_be_valid_attribute(org)
        self._description_type_should_be_valid_attribute(org)
        self._locale_should_be_valid_attribute(org)

    def _concept_class_should_be_valid_attribute(self, org):
        is_concept_class_valid = self._is_attribute_valid(self.concept_class, org, 'Classes', 'Concept Class')

        if not is_concept_class_valid:
            raise ValidationError({'names': ['Concept class should be valid attribute']})

    def _data_type_should_be_valid_attribute(self, org):
        is_data_type_valid = self._is_attribute_valid(self.datatype, org, 'Datatypes', 'Datatype')

        if not is_data_type_valid:
            raise ValidationError({'names': ['Data type should be valid attribute']})

    def _name_type_should_be_valid_attribute(self, org):
        name_type_count = len(
            filter(lambda n: self._is_attribute_valid(n.type, org, 'NameTypes', 'NameType'), self.names))

        if name_type_count < len(self.names):
            raise ValidationError({'names': ['Name type should be valid attribute']})

    def _description_type_should_be_valid_attribute(self, org):
        description_type_count = len(
            filter(lambda d: self._is_attribute_valid(d.type, org, 'DescriptionTypes', 'DescriptionType'),
                   self.descriptions))

        if description_type_count < len(self.descriptions):
            raise ValidationError({'names': ['Description type should be valid attribute']})

    def _locale_should_be_valid_attribute(self, org):
        name_locale_count = len(
            filter(lambda n: self._is_attribute_valid(n.locale, org, 'Locales', 'Locale'),
                   self.names))

        if name_locale_count < len(self.names):
            raise ValidationError({'names': ['Name locale should be valid attribute']})

        description_locale_count = len(
            filter(lambda d: self._is_attribute_valid(d.locale, org, 'Locales', 'Locale'),
                   self.descriptions))

        if description_locale_count < len(self.descriptions):
            raise ValidationError({'names': ['Description locale should be valid attribute']})

    def _is_attribute_valid(self, attribute_property, org, source_mnemonic, concept_class):
        attributetypes_source_filter = Source.objects.filter(parent_id=org.id, mnemonic=source_mnemonic)

        if attributetypes_source_filter.count() < 1:
            raise ValidationError({'names': ['Lookup attributes must be imported']})

        source_attributetypes = attributetypes_source_filter.values_list('id').get()

        from concepts.models import Concept
        matching_attribute_types = {'retired': False, 'is_active': True, 'concept_class': concept_class,
                                    'parent_id': source_attributetypes[0], 'names.name': attribute_property}

        if Concept.objects.raw_query(matching_attribute_types).count() > 0:
            return True