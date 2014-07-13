from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from djangotoolbox.fields import ListField, EmbeddedModelField
from oclapi.models import SubResourceBaseModel, ResourceVersionModel, VERSION_TYPE
from sources.models import SourceVersion

CONCEPT_TYPE = 'Concept'


class Concept(SubResourceBaseModel):
    concept_class = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    names = ListField(EmbeddedModelField('LocalizedText'))
    descriptions = ListField(EmbeddedModelField('LocalizedText'))
    retired = models.BooleanField(default=False)

    @property
    def display_name(self):
        return self.get_display_name_for(self)

    @property
    def display_locale(self):
        return self.get_display_locale_for(self)

    @property
    def owner_name(self):
        return self.parent.parent_resource

    @property
    def owner_type(self):
        return self.parent.parent_resource_type

    @property
    def num_versions(self):
        return ConceptVersion.objects.filter(versioned_object_id=self.id).count()

    @classmethod
    def resource_type(cls):
        return CONCEPT_TYPE

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        user = kwargs.pop('owner', None)
        if not user:
            errors['owner'] = 'Concept owner cannot be null.'
        parent_resource = kwargs.pop('parent_resource', None)
        if not parent_resource:
            errors['parent'] = 'Concept parent cannot be null.'
        if errors:
            return errors
        obj.owner = user
        obj.parent = parent_resource
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
        if errors:
            return errors

        parent_resource_version = kwargs.pop('parent_resource_version', None)
        if parent_resource_version is None:
            parent_resource_version = parent_resource.get_version_model().get_latest_version_of(parent_resource)
        child_list_attribute = kwargs.pop('child_list_attribute', 'concepts')

        initial_parent_children = getattr(parent_resource_version, child_list_attribute) or []
        initial_version = None
        errored_action = 'saving concept'
        persisted = False
        try:
            obj.save(**kwargs)

            # Create the initial version
            errored_action = 'creating initial version of concept'
            initial_version = ConceptVersion.for_concept(obj, '_TEMP')
            initial_version.save()
            initial_version.mnemonic = initial_version.id
            initial_version.released = True
            initial_version.save()

            # Associate the version with a version of the parent
            errored_action = 'associating concept with parent'
            parent_children = getattr(parent_resource_version, child_list_attribute) or []
            parent_children.append(initial_version.id)
            setattr(parent_resource_version, child_list_attribute, parent_children)
            parent_resource_version.save()

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
                setattr(parent_resource_version, initial_parent_children)
                parent_resource_version.save()
                if initial_version:
                    initial_version.delete()
                obj.delete()
        return errors

    @classmethod
    def retire(cls, concept):
        if concept.retired:
            return False
        concept.retired = True
        latest_version = ConceptVersion.get_latest_version_of(concept)
        retired_version = latest_version.clone()
        retired_version.retired = True
        latest_source_version = SourceVersion.get_latest_version_of(concept.parent)
        latest_source_version_concepts = latest_source_version.concepts
        retired = False
        try:
            concept.save()

            retired_version.save()
            retired_version.mnemonic = retired_version.id
            retired_version.save()

            latest_source_version.update_concept_version(retired_version)
            latest_source_version.save()
            retired = True
        finally:
            if not retired:
                latest_source_version.concepts = latest_source_version_concepts
                latest_source_version.save()
                retired_version.delete()
                concept.retired = False
                concept.save()
        return retired

    @staticmethod
    def get_url_kwarg():
        return 'concept'

    @staticmethod
    def get_display_name_for(obj):
        if not obj.names:
            return None
        for name in obj.names:
            if name.locale_preferred:
                return name.name
        return obj.names[0].name

    @staticmethod
    def get_display_locale_for(obj):
        if not obj.names:
            return None
        for name in obj.names:
            if name.locale_preferred:
                return name.locale
        return obj.names[0].locale

    @staticmethod
    def get_version_model():
        return ConceptVersion


class LocalizedText(models.Model):
    name = models.TextField()
    locale = models.TextField()
    locale_preferred = models.BooleanField(default=False)
    type = models.TextField(null=True, blank=True)


class ConceptVersion(ResourceVersionModel):
    concept_class = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    names = ListField(EmbeddedModelField('LocalizedText'))
    descriptions = ListField(EmbeddedModelField('LocalizedText'))
    retired = models.BooleanField(default=False)

    def clone(self):
        return ConceptVersion(
            mnemonic='_TEMP',
            concept_class=self.concept_class,
            datatype=self.datatype,
            names=self.names,
            descriptions=self.descriptions,
            retired=self.retired,
            versioned_object_id=self.versioned_object_id,
            versioned_object_type=self.versioned_object_type,
            released=self.released,
            previous_version=self,
            parent_version=self.parent_version
        )

    @property
    def name(self):
        return self.versioned_object.mnemonic

    @property
    def owner_name(self):
        return self.versioned_object.owner_name

    @property
    def owner_type(self):
        return self.versioned_object.owner_type

    @property
    def display_name(self):
        return Concept.get_display_name_for(self)

    @property
    def display_locale(self):
        return Concept.get_display_locale_for(self)

    @classmethod
    def for_concept(cls, concept, label, previous_version=None, parent_version=None):
        return ConceptVersion(
            mnemonic=label,
            concept_class=concept.concept_class,
            datatype=concept.datatype,
            names=concept.names,
            descriptions=concept.descriptions,
            retired=concept.retired,
            versioned_object_id=concept.id,
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            released=False,
            previous_version=previous_version,
            parent_version=parent_version
        )

    @classmethod
    def persist_clone(cls, obj, **kwargs):
        errors = dict()
        source_version = SourceVersion.get_latest_version_of(obj.versioned_object.parent)
        persisted = False
        errored_action = 'saving new concept version'
        try:
            obj.save(**kwargs)
            obj.mnemonic = obj.id
            obj.save()

            errored_action = 'replacing previous version in latest version of source'
            source_version.update_concept_version(obj)
            source_version.save()

            persisted = True
        finally:
            if not persisted:
                source_version.update_concept_version(obj.previous_version)
                obj.delete()
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
        return errors

    @classmethod
    def resource_type(cls):
        return VERSION_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'concept_version'

admin.site.register(Concept)
admin.site.register(ConceptVersion)