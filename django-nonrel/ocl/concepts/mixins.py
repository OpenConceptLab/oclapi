from django.core.exceptions import ValidationError

from concepts.custom_validators import OpenMRSConceptValidator
from sources.models import CUSTOM_VALIDATION_SCHEMA_OPENMRS

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
        self._requires_at_least_one_fully_specified_name()
        self._preferred_name_should_be_unique_for_source_and_locale()

        source = None

        if hasattr(self, "parent") and hasattr(self.parent, "custom_validation_schema"):
            source = self.parent
        elif hasattr(self, "source") and hasattr(self.source, "custom_validation_schema"):
            source = self.source

        if source is not None and source.custom_validation_schema == CUSTOM_VALIDATION_SCHEMA_OPENMRS:
            custom_validator = OpenMRSConceptValidator(self)
            custom_validator.validate()

    # basic validation rule
    def _preferred_name_should_be_unique_for_source_and_locale(self):
        # Concept preferred_name should be unique for same source and locale.
        validation_error = {'names': ['Concept preferred name should be unique for same source and locale']}
        preferred_names_in_concept = dict()
        name_id = lambda n: n.locale + n.name
        for name in self.names:
            if not name.locale_preferred:
                continue

            # making sure names in the submitted concept meet the same rule
            if preferred_names_in_concept.has_key(name_id(name)):
                raise ValidationError(validation_error)

            preferred_names_in_concept[name_id(name)] = True

            # querying the preferred names in source for the same rule
            raw_query = {'parent_id': self.parent.id, 'names.name': name.name, 'names.locale': name.locale,
                         'names.locale_preferred': True}

            #TODO find a better solution for circular dependency
            from concepts.models import Concept
            if Concept.objects.raw_query(raw_query).count() > 0:
                raise ValidationError(validation_error)

    def _requires_at_least_one_fully_specified_name(self):
        # Concept requires at least one fully specified name
        fully_specified_name_count = len(
            filter(lambda n: n.is_fully_specified, self.names))
        if fully_specified_name_count < 1:
            raise ValidationError({'names': ['Concept requires at least one fully specified name']})
