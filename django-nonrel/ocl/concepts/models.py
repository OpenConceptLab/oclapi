from urlparse import urljoin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField, EmbeddedModelField
from concepts.mixins import DictionaryItemMixin
from oclapi.models import SubResourceBaseModel, ResourceVersionModel, VERSION_TYPE
from oclapi.utils import reverse_resource, reverse_resource_version
from orgs.models import Organization
from sources.models import SourceVersion


class LocalizedText(models.Model):
    name = models.TextField()
    locale = models.TextField()
    locale_preferred = models.BooleanField(default=False)
    type = models.TextField(null=True, blank=True)


CONCEPT_TYPE = 'Concept'


class Concept(SubResourceBaseModel, DictionaryItemMixin):
    concept_class = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    names = ListField(EmbeddedModelField(LocalizedText))
    descriptions = ListField(EmbeddedModelField(LocalizedText))
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
    def owner_url(self):
        return self.parent.parent_url

    @property
    def num_versions(self):
        return ConceptVersion.objects.filter(versioned_object_id=self.id).count()

    @classmethod
    def resource_type(cls):
        return CONCEPT_TYPE

    @classmethod
    def create_initial_version(cls, obj, **kwargs):
        initial_version = ConceptVersion.for_concept(obj, '_TEMP')
        initial_version.save()
        initial_version.mnemonic = initial_version.id
        initial_version.root_version = initial_version
        initial_version.released = True
        initial_version.save()
        return initial_version

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


class ConceptVersion(ResourceVersionModel):
    concept_class = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    names = ListField(EmbeddedModelField('LocalizedText'))
    descriptions = ListField(EmbeddedModelField('LocalizedText'))
    retired = models.BooleanField(default=False)
    root_version = models.ForeignKey('self', null=True, blank=True)

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
            parent_version=self.parent_version,
            root_version=self.root_version,
        )

    @property
    def name(self):
        return self.versioned_object.mnemonic

    @property
    def owner_url(self):
        if isinstance(self.versioned_object.owner, Organization):
            return reverse_resource(self.versioned_object.owner, 'organization-detail')
        else:
            kwargs = {'user': self.versioned_object.owner.username}
            return reverse('userprofile-detail', kwargs=kwargs)

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

    @property
    def source(self):
        return self.versioned_object.parent

    @property
    def mappings_url(self):
        return reverse_resource(self.versioned_object, 'mapping-list')

    @classmethod
    def for_concept(cls, concept, label, previous_version=None, parent_version=None):
        return ConceptVersion(
            mnemonic=label,
            concept_class=concept.concept_class,
            datatype=concept.datatype,
            extras=concept.extras,
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

    @classmethod
    def versioned_object_type(cls):
        return CONCEPT_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'concept_version'


class ConceptReference(SubResourceBaseModel, DictionaryItemMixin):
    concept = models.ForeignKey(Concept)
    concept_version = models.ForeignKey(ConceptVersion, null=True, blank=True)
    source_version = models.ForeignKey(SourceVersion, null=True, blank=True)

    def clean(self):
        if self.concept_version and self.source_version:
            raise ValidationError('Cannot specify both source_version and concept_version.')

    @property
    def concept_reference_url(self):
        if self.source_version:
            source_version_url = reverse_resource_version(self.source_version, 'sourceversion-detail')
            return urljoin(source_version_url, 'concepts/%s/' % self.concept.mnemonic)
        if self.concept_version:
            return reverse_resource_version(self.concept_version, 'conceptversion-detail')
        return reverse_resource(self.concept, 'concept-detail')

    @property
    def concept_class(self):
        return self.concept.concept_class if self.concept else None

    @property
    def data_type(self):
        return self.concept.datatype if self.concept else None

    @property
    def source(self):
        return self.concept.parent if self.concept else None

    @property
    def owner_name(self):
        return self.parent.parent_resource if self.parent else None

    @property
    def owner_type(self):
        return self.parent.parent_resource_type if self.parent else None

    @property
    def owner_url(self):
        return self.parent.parent_url if self.parent else None

    @property
    def display_name(self):
        return self.concept.display_name if self.concept else None

    @property
    def display_locale(self):
        return self.concept.display_locale if self.concept else None

    @property
    def is_current_version(self):
        return not(self.concept_version or self.source_version)

    @staticmethod
    def get_url_kwarg():
        return 'concept'


@receiver(post_save, sender=User)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if instance.is_active:
        for concept in Concept.objects.filter(owner=instance):
            concept.undelete()
    else:
        for concept in Concept.objects.filter(owner=instance):
            concept.soft_delete()
