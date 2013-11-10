from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from djangotoolbox.fields import ListField, EmbeddedModelField
from oclapi.models import SubResourceBaseModel, ResourceVersionModel, VERSION_TYPE

CONCEPT_TYPE = 'Concept'


class Concept(SubResourceBaseModel):
    concept_class = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    names = ListField(EmbeddedModelField('LocalizedText'))
    descriptions = ListField(EmbeddedModelField('LocalizedText'))

    @property
    def display_name(self):
        if not self.names:
            return None
        for name in self.names:
            if name.locale_preferred:
                return name.name
        return self.names[0].name

    @property
    def display_locale(self):
        if not self.names:
            return None
        for name in self.names:
            if name.locale_preferred:
                return name.locale
        return self.names[0].locale

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

    @staticmethod
    def get_url_kwarg():
        return 'concept'


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

    @classmethod
    def for_concept(cls, concept, label, previous_version=None, parent_version=None):
        return ConceptVersion(
            mnemonic=label,
            concept_class=concept.concept_class,
            datatype=concept.datatype,
            names=concept.names,
            descriptions=concept.descriptions,
            versioned_object_id=concept.id,
            versioned_object_type=ContentType.objects.get_for_model(Concept),
            released=False,
            previous_version=previous_version,
            parent_version=parent_version
        )

    @classmethod
    def resource_type(cls):
        return VERSION_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'version'

admin.site.register(Concept)
admin.site.register(ConceptVersion)