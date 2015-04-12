from boto.s3.connection import S3Connection
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField
from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel
from oclapi.utils import S3ConnectionFactory

SOURCE_TYPE = 'Source'


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
    concepts = ListField()
    mappings = ListField()

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

    def seed_concepts(self):
        seed_concepts_from = self.previous_version or self.parent_version
        if seed_concepts_from:
            self.concepts = list(seed_concepts_from.concepts)

    def seed_mappings(self):
        seed_mappings_from = self.previous_version or self.parent_version
        if seed_mappings_from:
            self.mappings = list(seed_mappings_from.mappings)

    def has_export(self):
        bucket = S3ConnectionFactory.get_export_bucket()
        return bucket.get_key(self.export_path)

    @property
    def export_path(self):
        last_update = self.updated_at.strftime('%Y%m%d%H%M%S')
        source = self.versioned_object
        return "%s/%s_%s.%s.tgz" % (source.owner_name, source.mnemonic, self.mnemonic, last_update)

    @property
    def resource_type(self):
        return SOURCE_VERSION_TYPE

    @classmethod
    def for_base_object(cls, source, label, previous_version=None, parent_version=None, released=False):
        if not Source == type(source):
            raise ValidationError("source must be of type 'Source'")
        if not source.id:
            raise ValidationError("source must have an Object ID.")
        return SourceVersion(
            mnemonic=label,
            name=source.name,
            full_name=source.full_name,
            source_type=source.source_type,
            public_access=source.public_access,
            default_locale=source.default_locale,
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
            external_id=source.external_id
        )

@receiver(post_save)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return False
    for source in Source.objects.filter(parent_id=instance.id, parent_type=ContentType.objects.get_for_model(sender)):
        if instance.is_active != source.is_active:
            source.undelete() if instance.is_active else source.soft_delete()
