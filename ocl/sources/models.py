from bson import ObjectId
from celery.result import AsyncResult
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField, DictField

from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from oclapi.utils import S3ConnectionFactory, get_class, update_search_index
from datetime import datetime

SOURCE_TYPE = 'Source'

HEAD = 'HEAD'

class Source(ConceptContainerModel):
    source_type = models.TextField(blank=True)

    class MongoMeta:
        indexes = [[('uri', 1)]]

    @property
    def concepts_url(self):
        owner = self.owner
        owner_kwarg = 'user' if isinstance(owner, User) else 'org'
        return reverse('concept-create', kwargs={'source': self.mnemonic, owner_kwarg: owner.mnemonic})

    @property
    def versions_url(self):
        owner = self.owner
        owner_kwarg = 'user' if isinstance(owner, User) else 'org'
        return reverse('sourceversion-list', kwargs={'source': self.mnemonic, owner_kwarg: owner.mnemonic})

    def get_head(self):
        return SourceVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.id)

    @property
    def public_can_view(self):
        return self.public_access in [ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW]

    @classmethod
    def resource_type(cls):
        return SOURCE_TYPE

    @classmethod
    def get_version_model(cls):
        return SourceVersion

    @staticmethod
    def get_url_kwarg():
        return 'source'


SOURCE_VERSION_TYPE = 'Source Version'


class SourceVersion(ConceptContainerVersionModel):
    source_type = models.TextField(blank=True)
    custom_validation_schema = models.TextField(blank=True, null=True)
    retired = models.BooleanField(default=False)
    #TODO: remove concept and mappings fields after migration on all envs
    concepts = ListField()
    mappings = ListField()
    active_concepts = models.IntegerField(default=0)
    active_mappings = models.IntegerField(default=0)
    _ocl_processing = models.BooleanField(default=False)
    source_snapshot = DictField(null=True, blank=True)

    class MongoMeta:
        indexes = [[('versioned_object_id', 1), ('is_active', 1), ('created_at', 1)],
                   [('versioned_object_id', 1), ('versioned_object_type', 1)],
                   [('versioned_object_id', 1), ('mnemonic', 1)],
                   [('uri', 1)]]

    #TODO: remove once concept and mappings fields are migrated on all envs
    @classmethod
    def migrate_concepts_and_mappings_field(cls):
        source_versions = SourceVersion.objects.all()
        source_versions_count = SourceVersion.objects.count()
        source_versions_pos = 0
        for source_version in source_versions:
            source_versions_pos = source_versions_pos + 1
            if len(source_version.concepts) == 0 and len(source_version.mappings) == 0:
                continue

            print 'Migrating source %s (%s of %s)' % (source_version.mnemonic, source_versions_pos, source_versions_count)

            concepts = map((lambda x: ObjectId(x)), source_version.concepts)
            from concepts.models import ConceptVersion
            ConceptVersion.objects.raw_update({'_id': {'$in': concepts}}, {'$push': { 'source_version_ids': source_version.id }})
            ConceptVersion.objects.filter(id__in=source_version.concepts).update(updated_at=datetime.now())

            mappings = map((lambda x: ObjectId(x)), source_version.mappings)
            from mappings.models import MappingVersion
            MappingVersion.objects.raw_update({'_id': {'$in': mappings}},
                                              {'$push': {'source_version_ids': source_version.id}})
            MappingVersion.objects.filter(id__in=source_version.mappings).update(updated_at=datetime.now())

            source_version.concepts = []
            source_version.mappings = []
            source_version.save()

    def update_concept_version(self, concept_version):
        concept_previous_version = concept_version.previous_version

        if concept_previous_version:
            from concepts.models import ConceptVersion
            # Using raw query to atomically remove item from the list
            ConceptVersion.objects.raw_update({'_id': ObjectId(concept_previous_version.id)},
                                              {'$pull': {'source_version_ids': self.id}})
            ConceptVersion.objects.filter(id=concept_previous_version.id).update(updated_at=datetime.now())
            update_search_index(concept_previous_version)

        self.add_concept_version(concept_version)

    def add_concept_version(self, concept_version):
        from concepts.models import ConceptVersion
        # Using raw query to atomically add item to the list
        ConceptVersion.objects.raw_update({'_id': ObjectId(concept_version.id)},
                                          {'$push': {'source_version_ids': self.id}})
        ConceptVersion.objects.filter(id=concept_version.id).update(updated_at=datetime.now())
        update_search_index(concept_version)

    def has_concept_version(self, concept_version):
        return self.id in concept_version.source_version_ids

    def update_mapping_version(self, mapping_version):
        mapping_previous_version = mapping_version.previous_version

        if mapping_previous_version:
            from mappings.models import MappingVersion
            #Using raw query to atomically remove item from the list
            MappingVersion.objects.raw_update({'_id': ObjectId(mapping_previous_version.id)},{'$pull': {'source_version_ids': self.id}})
            MappingVersion.objects.filter(id=mapping_previous_version.id).update(updated_at=datetime.now())
            update_search_index(mapping_previous_version)

        self.add_mapping_version(mapping_version)

    def add_mapping_version(self, mapping_version):
        from mappings.models import MappingVersion
        # Using raw query to atomically add item to the list
        MappingVersion.objects.raw_update({'_id': ObjectId(mapping_version.id)},
                                          {'$push': {'source_version_ids': self.id}})
        MappingVersion.objects.filter(id=mapping_version.id).update(updated_at=datetime.now())
        update_search_index(mapping_version)

    def has_mapping_version(self, mapping_version):
        return self.id in mapping_version.source_version_ids

    def get_concepts(self):
        from concepts.models import ConceptVersion
        return ConceptVersion.objects.filter(source_version_ids__contains=self.id)

    def get_concept_ids(self):
        from concepts.models import ConceptVersion
        return ConceptVersion.objects.filter(source_version_ids__contains=self.id).values_list('id', flat=True)

    def get_mappings(self):
        from mappings.models import MappingVersion
        return MappingVersion.objects.filter(source_version_ids__contains=self.id)

    def get_mapping_ids(self):
        from mappings.models import MappingVersion
        return MappingVersion.objects.filter(source_version_ids__contains=self.id).values_list('id', flat=True)

    def seed_concepts(self):
        seed_concepts_from = self.head_sibling()
        if seed_concepts_from:
            from concepts.models import ConceptVersion
            ConceptVersion.objects.raw_update({'source_version_ids': seed_concepts_from.id}, {'$push': { 'source_version_ids': self.id }})

    def head_sibling(self):
        try:
            return SourceVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.versioned_object_id)
        except Exception as e:
            return None

    def seed_mappings(self):
        seed_mappings_from = self.head_sibling()
        if seed_mappings_from:
            from mappings.models import MappingVersion
            MappingVersion.objects.raw_update({'source_version_ids': seed_mappings_from.id},
                                              {'$push': {'source_version_ids': self.id}})

    def update_version_data(self, obj=None):
        if obj:
            self.description = obj.description
        else:
            obj = self.head_sibling()

        if obj:
            self.name = obj.name
            self.full_name = obj.full_name
            self.website = obj.website
            self.public_access = obj.public_access
            self.source_type = obj.source_type
            self.supported_locales = obj.supported_locales
            self.custom_validation_schema = obj.custom_validation_schema
            self.default_locale = obj.default_locale
            self.external_id = obj.external_id


    def get_export_key(self):
        bucket = S3ConnectionFactory.get_export_bucket()
        return bucket.get_key(self.export_path)

    def has_export(self):
        return bool(self.get_export_key())

    @property
    def export_path(self):
        last_update = self.last_child_update.strftime('%Y%m%d%H%M%S')
        source = self.versioned_object
        return "%s/%s_%s.%s.tgz" % (source.owner_name, source.mnemonic, self.mnemonic, last_update)

    @property
    def last_child_update(self):
        last_concept_update = self.last_concept_update
        last_mapping_update = self.last_mapping_update
        if last_concept_update and last_mapping_update:
            return max(last_concept_update, last_mapping_update)
        return last_concept_update or last_mapping_update or self.updated_at

    @property
    def last_concept_update(self):
        concepts = self.get_concepts()
        if not concepts.exists():
            return None
        agg = concepts.aggregate(Max('updated_at'))
        return agg.get('updated_at__max')

    @property
    def last_mapping_update(self):
        mappings = self.get_mappings()
        if not mappings.exists():
            return None
        agg = mappings.aggregate(Max('updated_at'))
        return agg.get('updated_at__max')

    @property
    def resource_type(self):
        return SOURCE_VERSION_TYPE

    @classmethod
    def for_base_object(cls, source, label, previous_version=None, parent_version=None, released=False):
        if not Source == type(source):
            raise ValidationError("source must be of type 'Source'")
        if not source.id:
            raise ValidationError("source must have an Object ID.")

        mnemonic = label
        if label == 'INITIAL':
            mnemonic = HEAD

        return SourceVersion(
            mnemonic=mnemonic,
            name=source.name,
            full_name=source.full_name,
            source_type=source.source_type,
            public_access=source.public_access,
            default_locale=source.default_locale,
            custom_validation_schema=source.custom_validation_schema,
            supported_locales=source.supported_locales,
            website=source.website,
            description=source.description,
            versioned_object_id=source.id,
            versioned_object_type=ContentType.objects.get_for_model(type(source)),
            released=released,
            previous_version=previous_version,
            parent_version=parent_version,
            created_by=source.created_by,
            updated_by=source.updated_by,
            external_id=source.external_id,
            extras=source.extras,
        )

@receiver(post_save)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return False
    for source in Source.objects.filter(parent_id=instance.id, parent_type=ContentType.objects.get_for_model(sender)):
        if instance.is_active != source.is_active:
            source.undelete() if instance.is_active else source.soft_delete()
