from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from concepts.models import Concept, ConceptVersion
from oclapi.models import SubResourceBaseModel
from oclapi.utils import reverse_resource

MAPPING_RESOURCE_TYPE = 'Mapping'


class Mapping(SubResourceBaseModel):
    map_type = models.TextField()
    to_concept = models.ForeignKey(Concept, null=True, blank=True, related_name='mappings_to')
    to_source_url = models.URLField(null=True, blank=True)
    to_concept_name = models.TextField(null=True, blank=True)
    to_concept_code = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (
            ("parent_id", "parent_type", "map_type", "to_concept"),
            ("parent_id", "parent_type", "map_type", "to_source_url", "to_concept_name", "to_concept_code")
        )

    def clean(self, exclude=None):
        if not (self.to_concept or (self.to_source_url and self.to_concept_name and self.to_concept_code)):
            raise ValidationError("Must specify either 'to_concept' or 'to_source_url', 'to_concept_name' & 'to_concept_code'")
        if self.to_concept and self.to_source_url and self.to_concept_name and self.to_concept_code:
            raise ValidationError("Must specify one of 'to_concept' or 'to_source_url', 'to_concept_name' & 'to_concept_code'.  Cannot specify both.")

    def get_to_source_url(self):
        return self.to_source_url or reverse_resource(self.to_concept.parent, 'source-detail')

    def get_to_concept_name(self):
        return self.to_concept_name or self.to_concept.display_name

    def get_to_concept_code(self):
        return self.to_concept_code or self.to_concept.mnemonic

    @property
    def to_source_name(self):
        return self.to_concept.parent.mnemonic if self.to_concept else None

    @property
    def to_source_owner(self):
        return self.to_concept.parent.parent.mnemonic if self.to_concept else None

    @property
    def from_concept_code(self):
        return self.parent.mnemonic

    @property
    def from_source(self):
        return self.parent.parent

    @property
    def from_source_name(self):
        return self.parent.parent.mnemonic

    @property
    def from_source_shorthand(self):
        source = self.from_source
        owner = source.parent
        return "%s:%s" % (owner.mnemonic, source.mnemonic)

    @property
    def from_concept_shorthand(self):
        return "%s:%s" % (self.from_source_shorthand, self.parent.mnemonic)

    @property
    def to_source_shorthand(self):
        if not self.to_concept:
            return None
        source = self.to_concept.parent
        owner = source.parent
        return "%s:%s" % (owner.mnemonic, source.mnemonic)

    @property
    def to_concept_shorthand(self):
        if not self.to_concept:
            return None
        return "%s:%s" % (self.to_source_shorthand, self.to_concept.mnemonic)

    @property
    def from_source_owner(self):
        return self.parent.parent.parent.mnemonic

    @staticmethod
    def resource_type():
        return MAPPING_RESOURCE_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'mapping'

    @classmethod
    def persist_changes(cls, obj, updated_by, **kwargs):
        created = kwargs.pop('created', False)
        errors = dict()
        try:
            obj.updated_by = updated_by
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
            return errors

        persisted = False
        try:
            obj.updated_by = updated_by
            obj.save(**kwargs)
            if created:
                obj.mnemonic = obj.id
                obj.save(**kwargs)

            # Create a new version of the "from" concept
            concept_version = ConceptVersion.get_latest_version_of(obj.parent)
            new_version = concept_version.clone()
            action = 'Added' if created else 'Updated'
            new_version.update_comment = "%s mapping: %s" % (action, obj.mnemonic)
            ConceptVersion.persist_clone(new_version)

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ["Failed to persist mapping."]
        return errors

    @classmethod
    def persist_new(cls, obj, updated_by, **kwargs):
        errors = dict()
        non_field_errors = []
        owner = kwargs.pop('owner', None)
        if owner is None:
            non_field_errors.append('Must specify an owner')
        obj.owner = owner
        obj.updated_by = owner
        parent_resource = kwargs.pop('parent_resource', None)
        if parent_resource is None:
            non_field_errors.append('Must specify a parent resource (the "from" concept).')
        obj.parent = parent_resource
        obj.public_access = parent_resource.public_access
        if non_field_errors:
            errors['non_field_errors'] = non_field_errors
            return errors
        obj.mnemonic = 'TEMP'
        kwargs.update({'created': True})
        return cls.persist_changes(obj, updated_by, **kwargs)


@receiver(post_save, sender=Concept)
def propagate_public_access(sender, instance=None, created=False, **kwargs):
    for mapping in Mapping.objects.filter(parent_id=instance.id):
        if instance.public_access != mapping.public_access:
            mapping.public_access = instance.public_access
            mapping.save()