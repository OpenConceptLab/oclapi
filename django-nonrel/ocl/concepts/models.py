from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
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
        user = kwargs.pop('owner')
        parent_resource = kwargs.pop('parent_resource')
        parent_resource_version = kwargs.pop('parent_resource_version', None)
        if parent_resource_version is None:
            parent_resource_version = parent_resource.get_version_model().get_latest_version_of(parent_resource)
        child_list_attribute = kwargs.pop('child_list_attribute', None)
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if Concept.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            errors['mnemonic'] = 'Concept with mnemonic %s already exists for parent resource %s.' % (mnemonic, parent_resource.mnemonic)
            return errors
        with transaction.commit_on_success():
            errored_action = 'saving concept'
            try:
                obj.parent = parent_resource
                obj.owner = user
                obj.save(**kwargs)

                # Create the initial version
                errored_action = 'creating initial version of concept'
                version = ConceptVersion.for_concept(obj, '_TEMP')
                version.released = True
                version.save()
                version.mnemonic = version.id
                version.save()

                # Associate the version with a version of the parent
                errored_action = 'associating concept with parent'
                children = getattr(parent_resource_version, child_list_attribute) or []
                children.append(version.id)
                setattr(parent_resource_version, child_list_attribute, children)
                parent_resource_version.save()
            except Exception as e:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
        return errors

    @classmethod
    def retire(cls, concept):
        concept.retired = True
        latest_version = ConceptVersion.get_latest_version_of(concept)
        retired_version = latest_version.clone()
        retired_version.retired = True
        latest_source_version = SourceVersion.get_latest_version_of(concept.parent)
        with transaction.commit_on_success():
            concept.save()

            retired_version.save()
            retired_version.mnemonic = retired_version.id
            retired_version.save()

            previous_version = retired_version.previous_version
            if previous_version:
                previous_version.next_version = retired_version
                previous_version.save()

            latest_source_version.update_concept_version(retired_version)
            latest_source_version.save()

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
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        with transaction.commit_on_success():
            errored_action = 'saving new concept version'
            try:
                obj.save(**kwargs)
                obj.mnemonic = obj.id
                obj.save()

                errored_action = 'setting next_version attribute on previous version'
                previous_version = obj.previous_version
                previous_version.next_version = obj
                previous_version.save()

                errored_action = 'replacing previous version in latest version of source'
                source_version = SourceVersion.get_latest_version_of(obj.versioned_object.parent)
                source_version.update_concept_version(obj)
                source_version.save()
            except Exception as e:
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