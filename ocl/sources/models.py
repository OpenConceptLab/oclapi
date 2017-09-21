from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField, DictField

from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW
from oclapi.utils import S3ConnectionFactory, get_class

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
                   [('versioned_object_id', 1), ('versioned_object_type', 1)]]

    #TODO: remove once concept and mappings fields are migrated on all envs
    @classmethod
    def migrate_concepts_and_mappings_field(cls):
        import haystack
        from datetime import datetime
        haystack.signal_processor = haystack.signals.BaseSignalProcessor
        import_start_time = datetime.now()

        source_versions = SourceVersion.objects.all();
        for source_version in source_versions:
            from concepts.models import ConceptVersion
            i = 0
            concept_versions_count = ConceptVersion.objects.filter(id__in = source_version.concepts).count()
            concept_versions = ConceptVersion.objects.filter(id__in = source_version.concepts).iterator()
            for concept_version in concept_versions:
                i = i + 1
                print 'Migrating concept %s (%s of %s)' % (concept_version.id, i, concept_versions_count)
                source_version.add_concept_version(concept_version)

            source_version.concepts = []
            source_version.save()

            from mappings.models import MappingVersion
            i = 0
            mapping_versions_count = MappingVersion.objects.filter(id__in=source_version.mappings).count()
            mapping_versions = MappingVersion.objects.filter(id__in=source_version.mappings).iterator()
            for mapping_version in mapping_versions:
                i = i + 1
                print 'Migrating mapping %s (%s of %s)' % (mapping_version.id, i, mapping_versions_count)
                source_version.add_mapping_version(mapping_version)


            source_version.mappings = []
            source_version.save()

        from haystack.management.commands import update_index
        update_index.Command().handle(start_date=import_start_time.strftime("%Y-%m-%dT%H:%M:%S"), verbosity=1,
                                      workers=8, batchsize=128)

        haystack.signal_processor = haystack.signals.RealtimeSignalProcessor

    def update_concept_version(self, concept_version):
        concept_previous_version = concept_version.previous_version

        try:
            source_version_concept = SourceVersionConcept.objects.get(source_version=self, concept_version=concept_previous_version)
            source_version_concept.concept_version = concept_version
            source_version_concept.full_clean()
            source_version_concept.save()
            #Trigger SOLR update
            concept_previous_version.save()
            concept_version.save()
        except SourceVersionConcept.DoesNotExist:
            self.add_concept_version(concept_version)

    @classmethod
    def get_concept_sources(cls, concept_version):
        source_version_ids = list(SourceVersionConcept.objects.filter(concept_version=concept_version).values_list('source_version', flat=True))
        return SourceVersion.objects.filter(id__in=source_version_ids)

    @classmethod
    def get_mapping_sources(cls, mapping_version):
        source_version_ids = list(
            SourceVersionMapping.objects.filter(mapping_version=mapping_version).values_list('source_version',
                                                                                             flat=True))
        return SourceVersion.objects.filter(id__in=source_version_ids)

    def add_concept_version(self, concept_version):
        if self.has_concept_version(concept_version):
            return

        source_version_concept = SourceVersionConcept(source_version=self, concept_version=concept_version)
        source_version_concept.full_clean()
        source_version_concept.save()

        # Trigger SOLR update
        concept_version.save()

    def has_concept_version(self, concept_version):
        return SourceVersionConcept.objects.filter(source_version=self, concept_version=concept_version).exists()

    def delete_concept_version(self, concept_version):
        SourceVersionConcept.objects.filter(source_version=self, concept_version=concept_version).delete();

    def update_mapping_version(self, mapping_version):
        mapping_previous_version = mapping_version.previous_version

        try:
            source_version_mapping = SourceVersionMapping.objects.get(source_version=self, mapping_version=mapping_previous_version)
            source_version_mapping.mapping_version = mapping_version
            source_version_mapping.full_clean()
            source_version_mapping.save()
            # Trigger SOLR update
            mapping_previous_version.save()
            mapping_version.save()
        except SourceVersionMapping.DoesNotExist:
            self.add_mapping_version(mapping_version)

    def add_mapping_version(self, mapping_version):
        if self.has_mapping_version(mapping_version):
            return

        source_version_mapping = SourceVersionMapping(source_version=self, mapping_version=mapping_version)
        source_version_mapping.full_clean()
        source_version_mapping.save()

        # Trigger SOLR update
        mapping_version.save()

    def has_mapping_version(self, mapping_version):
        return SourceVersionMapping.objects.filter(source_version=self, mapping_version=mapping_version).exists()

    def delete_mapping_version(self, mapping_version):
        SourceVersionMapping.objects.filter(source_version=self, mapping_version=mapping_version).delete();

    def get_concepts(self):
        from concepts.models import ConceptVersion
        concept_version_ids =  self.get_concept_ids()
        return ConceptVersion.objects.filter(id__in=concept_version_ids)

    def get_concept_ids(self):
        concept_version_ids = list(
            SourceVersionConcept.objects.filter(source_version=self).values_list('concept_version', flat=True))
        return concept_version_ids

    def get_mappings(self):
        from mappings.models import MappingVersion
        mapping_version_ids = self.get_mapping_ids()
        return MappingVersion.objects.filter(id__in=mapping_version_ids)

    def get_mapping_ids(self):
        mapping_version_ids = list(
            SourceVersionMapping.objects.filter(source_version=self).values_list('mapping_version', flat=True))
        return mapping_version_ids

    def seed_concepts(self):
        seed_concepts_from = self.head_sibling()
        if seed_concepts_from:
            concepts = seed_concepts_from.get_concepts()
            for concept in concepts:
                self.add_concept_version(concept)

    def head_sibling(self):
        try:
            return SourceVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.versioned_object_id)
        except Exception as e:
            return None

    def seed_mappings(self):
        seed_mappings_from = self.previous_version or self.parent_version
        if seed_mappings_from:
            mappings = seed_mappings_from.get_mappings()
            for mapping in mappings:
                self.add_mapping_version(mapping)

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

class SourceVersionConcept(models.Model):

    source_version = models.ForeignKey(SourceVersion, null=False, blank=False)
    concept_version = models.ForeignKey('concepts.ConceptVersion', null=False, blank=False, db_index=True)

    class Meta:
        unique_together = (('source_version', 'concept_version'),)


class SourceVersionMapping(models.Model):

    source_version = models.ForeignKey(SourceVersion, null=False, blank=False)
    mapping_version = models.ForeignKey('mappings.MappingVersion', null=False, blank=False, db_index=True)

    class Meta:
        unique_together = (('source_version', 'mapping_version'),)

@receiver(post_save)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return False
    for source in Source.objects.filter(parent_id=instance.id, parent_type=ContentType.objects.get_for_model(sender)):
        if instance.is_active != source.is_active:
            source.undelete() if instance.is_active else source.soft_delete()
