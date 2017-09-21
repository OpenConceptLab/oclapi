from django.core.exceptions import ValidationError

from concepts.custom_validators import OpenMRSConceptValidator
from concepts.validators import BasicConceptValidator, ValidatorSpecifier
from oclapi.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS
import os

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
            parent_resource_version.add_concept_version(initial_version)

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]

                if initial_version:
                    parent_resource_version.delete_concept_version(initial_version)
                    initial_version.delete()
                if obj.id:
                    obj.delete()
        return errors


class ConceptValidationMixin:
    def clean(self):
        if os.environ.get('DISABLE_VALIDATION'):
            return

        validators = [BasicConceptValidator()]

        schema = self.parent_source.custom_validation_schema
        if schema:
            custom_validator = ValidatorSpecifier()\
                .with_validation_schema(schema)\
                .with_repo(self.parent_source)\
                .with_reference_values()\
                .get()
            validators.append(custom_validator)

        for validator in validators:
            validator.validate(self)


