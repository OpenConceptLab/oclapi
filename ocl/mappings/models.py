from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import get_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from concepts.models import Concept
from mappings.mixins import MappingValidationMixin
from oclapi.models import BaseModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW, ResourceVersionModel
from sources.models import Source, SourceVersion

MAPPING_RESOURCE_TYPE = 'Mapping'
MAPPING_VERSION_RESOURCE_TYPE = 'MappingVersion'

class Mapping(MappingValidationMixin, BaseModel):
    parent = models.ForeignKey(Source, related_name='mappings_from')
    map_type = models.TextField()
    from_concept = models.ForeignKey(Concept, related_name='mappings_from')
    to_concept = models.ForeignKey(Concept, null=True, blank=True, related_name='mappings_to', db_index=False)
    to_source = models.ForeignKey(Source, null=True, blank=True, related_name='mappings_to', db_index=False)
    to_concept_code = models.TextField(null=True, blank=True)
    to_concept_name = models.TextField(null=True, blank=True)
    retired = models.BooleanField(default=False)
    external_id = models.TextField(null=True, blank=True)

    class MongoMeta:
        indexes = [[("parent", 1), ("map_type", 1), ("from_concept", 1), ("to_concept", 1), ("to_source", 1), ("to_concept_code", 1)],
                   [('parent', 1), ('map_type', 1), ('from_concept', 1), ('to_source', 1), ('to_concept_code', 1), ('to_concept_name', 1)],
                   [('parent', 1), ('from_concept', 1), ('to_concept', 1), ('is_active', 1), ('retired', 1)]]

    def clone(self, user):
        return Mapping(
            created_by=user,
            public_access=self.public_access,
            extras=self.extras,
            parent_id=self.parent_id,
            map_type=self.map_type,
            from_concept=self.from_concept,
            to_concept=self.to_concept,
            to_source=self.to_source,
            to_concept_code=self.to_concept_code,
            to_concept_name=self.to_concept_name,
            retired=self.retired,
            external_id=self.external_id,
        )

    @property
    def mnemonic(self):
        return self.id

    @property
    def source(self):
        return self.parent.mnemonic

    @property
    def parent_source(self):
        return self.parent

    @property
    def owner(self):
        return self.parent.owner_name

    @property
    def owner_type(self):
        return self.parent.owner_type

    @property
    def from_source(self):
        return self.from_concept.parent

    @property
    def from_source_owner(self):
        return self.from_source.owner_name

    @property
    def from_source_owner_mnemonic(self):
        return self.from_source.owner.mnemonic

    @property
    def from_source_owner_type(self):
        return self.from_source.owner_type

    @property
    def from_source_name(self):
        return self.from_source.mnemonic

    @property
    def from_source_url(self):
        self.from_source.url

    @property
    def from_source_shorthand(self):
        return "%s:%s" % (self.from_source_owner_mnemonic, self.from_source_name)

    @property
    def from_concept_code(self):
        return self.from_concept.mnemonic

    @property
    def from_concept_name(self):
        return self.from_concept.display_name

    @property
    def from_concept_url(self):
        return self.from_concept.url

    @property
    def from_concept_shorthand(self):
        return "%s:%s" % (self.from_source_shorthand, self.from_concept_code)

    def get_to_source(self):
        return self.to_source or self.to_concept and self.to_concept.parent

    @property
    def to_source_name(self):
        return self.get_to_source() and self.get_to_source().mnemonic

    @property
    def to_source_url(self):
        to_source = self.get_to_source()
        return to_source.url if to_source else None

    @property
    def to_source_owner(self):
        return self.get_to_source() and unicode(self.get_to_source().parent)

    @property
    def to_source_owner_mnemonic(self):
        return self.get_to_source() and self.get_to_source().owner.mnemonic

    @property
    def to_source_owner_type(self):
        return self.get_to_source() and self.get_to_source().owner_type

    @property
    def to_source_shorthand(self):
        return self.get_to_source() and "%s:%s" % (self.to_source_owner_mnemonic, self.to_source_name)

    def get_to_concept_name(self):
        return self.to_concept_name or (self.to_concept and self.to_concept.display_name)

    def get_to_concept_code(self):
        return self.to_concept_code or (self.to_concept and self.to_concept.mnemonic)

    @property
    def to_concept_url(self):
        return self.to_concept.url if self.to_concept else None

    @property
    def to_concept_shorthand(self):
        return "%s:%s" % (self.to_source_shorthand, self.get_to_concept_code)

    @property
    def public_can_view(self):
        return self.public_access in [ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW]

    @staticmethod
    def resource_type():
        return MAPPING_RESOURCE_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'mapping'

    @property
    def get_latest_version(self):
        return MappingVersion.objects.filter(versioned_object_id=self.id).order_by('-created_at')[:1][0]

    @classmethod
    def retire(cls, mapping, user, update_comment=None):
        if mapping.retired:
            return False
        latest_version= MappingVersion.get_latest_version_of(mapping)
        prev_latest_version = MappingVersion.objects.get(id=latest_version.id, is_latest_version=True);
        retired_version=latest_version.clone()
        retired_version.retired = True
        if update_comment:
            retired_version.update_comment = update_comment
        else:
            retired_version.update_comment = 'Mapping was retired'
        errors = MappingVersion.persist_clone(retired_version, user,prev_latest_version)
        if not errors:
            mapping.retired = True
            mapping.save()
        return errors


    @staticmethod
    def get_version_model():
        return MappingVersion

    @classmethod
    def persist_changes(cls, obj, updated_by, update_comment=None, **kwargs):
        errors = dict()
        obj.updated_by = updated_by
        try:
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
            return errors

        persisted = False
        try:
            source_version = SourceVersion.get_head_of(obj.parent)
            obj.save(**kwargs)

            prev_latest_version = MappingVersion.objects.get(versioned_object_id=obj.id, is_latest_version=True)
            prev_latest_version.is_latest_version = False
            prev_latest_version.save()

            new_latest_version  = MappingVersion.for_mapping(obj)
            new_latest_version.previous_version = prev_latest_version
            new_latest_version.update_comment = update_comment
            new_latest_version.mnemonic = int(prev_latest_version.mnemonic) + 1
            new_latest_version.save()

            source_version.update_mapping_version(new_latest_version)

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ["Failed to persist mapping."]
        return errors

    @classmethod
    def persist_new(cls, mapping, created_by, **kwargs):
        errors = dict()
        non_field_errors = []

        # Check for required fields
        if not created_by:
            non_field_errors.append('Must specify a creator')

        parent_resource = kwargs.pop('parent_resource', None)
        if not parent_resource:
            non_field_errors.append('Must specify a parent source')

        if non_field_errors:
            errors['non_field_errors'] = non_field_errors
            return errors

        # Populate required fields and validate
        mapping.created_by = created_by
        mapping.updated_by = created_by
        mapping.parent = parent_resource
        mapping.public_access = parent_resource.public_access

        try:
            mapping.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
            return errors

        # Get the parent source version and its initial list of mappings IDs
        parent_resource_version = kwargs.pop('parent_resource_version', None)
        if parent_resource_version is None:
            parent_resource_version = parent_resource.get_version_model().get_head_of(parent_resource)

        errored_action = 'saving mapping'
        persisted = False
        initial_version=None
        try:
            mapping.save(**kwargs)

            #Initial mapping version
            initial_version = MappingVersion.for_mapping(mapping)
            initial_version.mnemonic = 1
            initial_version.save()

            # Save again to get the correct URL
            mapping.save()

            errored_action = 'associating mapping with parent resource'
            parent_resource_version.add_mapping_version(initial_version)

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
                if initial_version and initial_version.id:
                    parent_resource_version.delete_mapping_version(initial_version)
                    initial_version.delete()
                if mapping.id:
                    mapping.delete()
        return errors

    @classmethod
    def diff(cls, v1, v2):
        diffs = {}
        if v1.public_access != v2.public_access:
            diffs['public_access'] = {'was': v1.public_access, 'is': v2.public_access}
        if v1.map_type != v2.map_type:
            diffs['map_type'] = {'was': v1.map_type, 'is': v2.map_type}
        if v1.from_concept != v2.from_concept:
            diffs['from_concept'] = {'was': v1.from_concept, 'is': v2.from_concept}
        if v1.to_concept != v2.to_concept:
            diffs['to_concept'] = {'was': v1.to_concept, 'is': v2.to_concept}
        if v1.to_source != v2.to_source:
            diffs['to_source'] = {'was': v1.to_source, 'is': v2.to_source}
        if v1.to_concept_code != v2.to_concept_code:
            diffs['to_concept_code'] = {'was': v1.to_concept_code, 'is': v2.to_concept_code}
        if v1.to_concept_name != v2.to_concept_name:
            diffs['to_concept_name'] = {'was': v1.to_concept_name, 'is': v2.to_concept_name}

        # Diff extras
        extras1 = v1.extras or {}
        extras2 = v2.extras or {}
        diff = len(extras1) != len(extras2)
        if not diff:
            for key in extras1:
                if key not in extras2:
                    diff = True
                    break
                if extras2[key] != extras1[key]:
                    diff = True
                    break
        if diff:
            diffs['extras'] = {'was': extras1, 'is': extras2}

        return diffs


class MappingVersion(MappingValidationMixin, ResourceVersionModel):
    parent = models.ForeignKey(Source, related_name='mappings_version_from')
    map_type = models.TextField()
    from_concept = models.ForeignKey(Concept, related_name='mappings_version_from')
    to_concept = models.ForeignKey(Concept, null=True, blank=True, related_name='mappings_version_to', db_index=False)
    to_source = models.ForeignKey(Source, null=True, blank=True, related_name='mappings_version_to', db_index=False)
    to_concept_code = models.TextField(null=True, blank=True)
    to_concept_name = models.TextField(null=True, blank=True)
    retired = models.BooleanField(default=False)
    external_id = models.TextField(null=True, blank=True)
    is_latest_version = models.BooleanField(default=True)
    update_comment = models.TextField(null=True, blank=True)

    def clone(self):
        return MappingVersion(
            mnemonic='--TEMP--',
            parent= self.parent,
            map_type=self.map_type,
            from_concept=self.from_concept,
            to_concept=self.to_concept,
            to_source=self.to_source,
            to_concept_code=self.to_concept_code,
            to_concept_name=self.to_concept_name,
            retired=self.retired,
            versioned_object_id=self.versioned_object_id,
            versioned_object_type=self.versioned_object_type,
            released=self.released,
            previous_version=self,
            parent_version=self.parent_version,
            is_latest_version=self.is_latest_version,
            extras=self.extras
        )

    class Meta:
        pass

    @property
    def source(self):
        return self.parent.mnemonic

    @property
    def parent_source(self):
        return self.parent

    @property
    def owner(self):
        return self.parent.owner_name

    @property
    def owner_type(self):
        return self.parent.owner_type

    @property
    def from_source(self):
        return self.from_concept.parent

    @property
    def from_source_owner(self):
        return self.from_source.owner_name

    @property
    def from_source_owner_mnemonic(self):
        return self.from_source.owner.mnemonic

    @property
    def from_source_owner_type(self):
        return self.from_source.owner_type

    @property
    def from_source_name(self):
        return self.from_source.mnemonic

    @property
    def from_source_url(self):
        return self.from_source.url

    @property
    def from_source_shorthand(self):
        return "%s:%s" % (self.from_source_owner_mnemonic, self.from_source_name)

    @property
    def from_concept_code(self):
        return self.from_concept.mnemonic

    @property
    def from_concept_name(self):
        return self.from_concept.display_name

    @property
    def from_concept_url(self):
        return self.from_concept.url

    @property
    def from_concept_shorthand(self):
        return "%s:%s" % (self.from_source_shorthand, self.from_concept_code)

    def get_to_source(self):
        return self.to_source or self.to_concept and self.to_concept.parent

    @property
    def to_source_name(self):
        return self.get_to_source() and self.get_to_source().mnemonic

    @property
    def to_source_url(self):
        to_source = self.get_to_source()
        return to_source.url if to_source else None

    @property
    def to_mapping_url(self):
        return self.versioned_object.uri

    @property
    def to_source_owner(self):
        return self.get_to_source() and unicode(self.get_to_source().parent)

    @property
    def to_source_owner_mnemonic(self):
        return self.get_to_source() and self.get_to_source().owner.mnemonic

    @property
    def to_source_owner_type(self):
        return self.get_to_source() and self.get_to_source().owner_type

    @property
    def to_source_shorthand(self):
        return self.get_to_source() and "%s:%s" % (self.to_source_owner_mnemonic, self.to_source_name)

    def get_to_concept_name(self):
        return self.to_concept_name or (self.to_concept and self.to_concept.display_name)

    def get_to_concept_code(self):
        return self.to_concept_code or (self.to_concept and self.to_concept.mnemonic)

    @property
    def to_concept_url(self):
        return self.to_concept.url if self.to_concept else None

    @property
    def to_concept_shorthand(self):
        return "%s:%s" % (self.to_source_shorthand, self.get_to_concept_code())

    @property
    def public_can_view(self):
        return self.public_access in [ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW]

    @staticmethod
    def resource_type():
        return MAPPING_VERSION_RESOURCE_TYPE

    @property
    def collection_versions(self):
        return get_model('collection', 'CollectionVersion').objects.filter(mappings=self.id)

    @staticmethod
    def get_url_kwarg():
        return 'mapping_version'

    @classmethod
    def for_mapping(cls, mapping, previous_version=None, parent_version=None):
        return MappingVersion(
            public_access=mapping.public_access,
            is_active=True,
            parent=mapping.parent,
            map_type=mapping.map_type,
            from_concept=mapping.from_concept,
            to_concept=mapping.to_concept,
            to_source=mapping.to_source,
            to_concept_code=mapping.to_concept_code,
            to_concept_name=mapping.to_concept_name,
            retired=mapping.retired,
            external_id=mapping.external_id,
            versioned_object_id=mapping.id,
            versioned_object_type=ContentType.objects.get_for_model(Mapping),
            released=False,
            previous_version=previous_version,
            parent_version=parent_version,
            created_by=mapping.created_by,
            updated_by=mapping.updated_by
        )

    @classmethod
    def get_latest_version_by_id(cls, id):
        versions = MappingVersion.objects.filter(versioned_object_id=id, is_latest_version=True).order_by('-created_at')
        return versions[0] if versions else None

    @classmethod
    def persist_clone(cls, obj, user=None, prev_latest_version=None, **kwargs):
        errors = dict()
        if not user:
            errors['version_created_by'] = 'Must specify which user is attempting to create a new concept version.'
            return errors
        obj.version_created_by = user.username
        previous_version = obj.previous_version
        previous_was_latest = previous_version.is_latest_version and obj.is_latest_version
        source_version = SourceVersion.get_head_of(obj.versioned_object.parent)

        persisted = False
        errored_action = 'saving new mapping version'
        try:
            obj.save(**kwargs)
            obj.mnemonic = int(prev_latest_version.mnemonic) + 1
            obj.save()

            errored_action = "updating 'is_latest_version' attribute on previous version"
            if previous_was_latest:
                previous_version.is_latest_version = False
                previous_version.save()

            errored_action = 'replacing previous version in latest version of source'
            source_version.update_mapping_version(obj)

            # Mark versioned object as updated
            mapping = obj.versioned_object
            mapping.save()

            persisted = True
        finally:
            if not persisted:
                source_version.update_mapping_version(obj.previous_version)
                if previous_was_latest:
                    previous_version.is_latest_version = True
                    previous_version.save()
                if obj.id:
                    obj.delete()
                errors['non_field_errors'] = ['An error occurred while %s.' % errored_action]
        return errors


@receiver(post_save, sender=Source)
def propagate_parent_attributes(sender, instance=None, created=False, **kwargs):
    if created:
        return
    for mapping in Mapping.objects.filter(parent_id=instance.id):
        update_index = False
        if mapping.is_active != instance.is_active:
            update_index = True
            mapping.is_active = instance.is_active
        if mapping.public_access != instance.public_access:
            update_index |= True
            mapping.public_access = instance.public_access
        if update_index:
            for mapping_version in MappingVersion.objects.filter(versioned_object_id=mapping.id):
                mapping_version.is_active = instance.is_active
                mapping_version.public_access = instance.public_access
                mapping_version.save()
            mapping.save()


@receiver(post_save, sender=Source)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return
    for mapping in Mapping.objects.filter(parent_id=instance.id):
        if (instance.is_active and not mapping.is_active) or (mapping.is_active and not instance.is_active):
            mapping.save()
