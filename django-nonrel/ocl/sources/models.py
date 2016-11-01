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
    concepts = ListField()
    mappings = ListField()
    retired = models.BooleanField(default=False)
    active_concepts = models.IntegerField(default=0)
    active_mappings = models.IntegerField(default=0)
    _ocl_processing = models.BooleanField(default=False)
    source_snapshot = DictField(null=True, blank=True)

    def update_concept_version(self, concept_version):
        previous_version = concept_version.previous_version
        save_previous_version = False
        if previous_version and previous_version.id in self.concepts:
            save_previous_version = True
            index = self.concepts.index(previous_version.id)
            self.concepts[index] = concept_version.id
        else:
            self.concepts.append(concept_version.id)
        self.save()
        concept_version.save()
        if save_previous_version:
            previous_version.save()

    def update_mapping_version(self, mapping_version):
        previous_version = mapping_version.previous_version
        save_previous_version = False
        if previous_version and previous_version.id in self.mappings:
            save_previous_version = True
            index = self.mappings.index(previous_version.id)
            self.mappings[index] = mapping_version.id
        else:
            self.mappings.append(mapping_version.id)
        self.save()
        mapping_version.save()
        if save_previous_version:
            previous_version.save()


    def seed_concepts(self):
        seed_concepts_from = self.head_sibling()
        if seed_concepts_from:
            self.concepts = list(seed_concepts_from.concepts)

    def head_sibling(self):
        try :
            return SourceVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.versioned_object_id)
        except Exception as e:
            return None

    def seed_mappings(self):
        seed_mappings_from = self.previous_version or self.parent_version
        if seed_mappings_from:
            self.mappings = list(seed_mappings_from.mappings)


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
        if not self.concepts:
            return None
        klass = get_class('concepts.models.ConceptVersion')
        versions = klass.objects.filter(id__in=self.concepts)
        if not versions.exists():
            return None
        agg = versions.aggregate(Max('updated_at'))
        return agg.get('updated_at__max')

    @property
    def last_mapping_update(self):
        if not self.mappings:
            return None
        klass = get_class('mappings.models.MappingVersion')
        mappings = klass.objects.filter(id__in=self.mappings)
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
