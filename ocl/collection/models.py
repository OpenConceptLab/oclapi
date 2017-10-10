from bson import ObjectId
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from djangotoolbox.fields import ListField, EmbeddedModelField, DictField

from collection.validation_messages import REFERENCE_ALREADY_EXISTS, CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE, \
    CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE
from oclapi.models import ConceptContainerModel, ConceptContainerVersionModel, ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW, CUSTOM_VALIDATION_SCHEMA_OPENMRS
from oclapi.utils import reverse_resource, S3ConnectionFactory, get_class, compact
from concepts.models import Concept, ConceptVersion
from mappings.models import Mapping, MappingVersion
from django.db.models import Max
from django.core.urlresolvers import reverse

COLLECTION_TYPE = 'Collection'
HEAD = 'HEAD'


class Collection(ConceptContainerModel):
    references = ListField(EmbeddedModelField('CollectionReference'))
    collection_type = models.TextField(blank=True)
    expressions = []

    @property
    def concepts_url(self):
        owner_kwarg = self.get_owner_type(self.owner)
        return reverse('concept-create', kwargs={'collection': self.mnemonic, owner_kwarg: self.owner.mnemonic})

    @property
    def mappings_url(self):
        owner_kwarg = self.get_owner_type(self.owner)
        return reverse('concept-mapping-list', kwargs={'collection': self.mnemonic, owner_kwarg: self.owner.mnemonic})

    @property
    def versions_url(self):
        return reverse_resource(self, 'collectionversion-list')

    def get_head(self):
        return CollectionVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.id)

    @property
    def resource_type(self):
        return COLLECTION_TYPE

    @property
    def public_can_view(self):
        return self.public_access in [ACCESS_TYPE_EDIT, ACCESS_TYPE_VIEW]

    @classmethod
    def get_version_model(cls):
        return CollectionVersion

    def clean(self):
        errors = self.add_references(self.expressions)
        if errors:
            raise ValidationError({'references': [errors]})

    def add_references(self, expressions):
        errors = {}
        for expression in expressions:
            ref = CollectionReference(expression=expression)
            try:
                self.validate(ref, expression)
            except Exception as e:
                errors[expression] = e.messages if hasattr(e, 'messages') else e
                continue

            self.references.append(ref)
            object_version = CollectionVersion.get_head(self.id)
            ref_hash = {'col_reference': ref}

            error = CollectionVersion.persist_changes(object_version, **ref_hash)
            if error:
                errors[expression] = error

        return errors


    def get_concept_id_by_version_information(self, expression):
        if CollectionReference.version_specified(expression):
            return ConceptVersion.objects.get(uri=expression).versioned_object_id
        else:
            return Concept.objects.get(uri=expression).id

    def validate(self, ref, expression):
        ref.full_clean()

        drop_version = CollectionReferenceUtils.drop_version
        if drop_version(ref.expression) in [drop_version(reference.expression) for reference in self.references]:
            raise ValidationError({expression: [REFERENCE_ALREADY_EXISTS]})

        if self.custom_validation_schema == CUSTOM_VALIDATION_SCHEMA_OPENMRS:
            if len(ref.concepts) < 1:
                return

            concept = ref.concepts[0]
            self.check_concept_uniqueness_in_collection_and_locale_by_name_attribute(concept, attribute='is_fully_specified', value=True,
                                                                                     error_message=CONCEPT_FULLY_SPECIFIED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE)
            self.check_concept_uniqueness_in_collection_and_locale_by_name_attribute(concept, attribute='locale_preferred', value=True,
                                                                                     error_message=CONCEPT_PREFERRED_NAME_UNIQUE_PER_COLLECTION_AND_LOCALE)

    def check_concept_uniqueness_in_collection_and_locale_by_name_attribute(self, concept, attribute, value, error_message):
        from concepts.models import Concept, ConceptVersion
        matching_names_in_concept = dict()

        for name in [n for n in concept.names if getattr(n, attribute) == value]:
            validation_error = {'names': [error_message]}
            # making sure names in the submitted concept meet the same rule
            name_key = name.locale + name.name
            if name_key in matching_names_in_concept:
                raise ValidationError(validation_error)

            matching_names_in_concept[name_key] = True

            other_concepts_in_collection = list(ConceptVersion.objects.filter(uri__in=self.current_references()).values_list('id', flat=True))

            if len(other_concepts_in_collection) < 1:
                continue

            other_concepts_in_collection = list(map(ObjectId, other_concepts_in_collection))

            same_name_and_locale = {'_id': {'$in': other_concepts_in_collection},
                                    'names': {'$elemMatch': {'name': name.name, 'locale': name.locale}}}

            if ConceptVersion.objects.raw_query(same_name_and_locale).count() > 0:
                raise ValidationError(validation_error)

    @classmethod
    def persist_changes(cls, obj, updated_by, **kwargs):
        obj.expressions = kwargs.pop('expressions', [])
        return super(Collection, cls).persist_changes(obj, updated_by, **kwargs)

    @staticmethod
    def get_url_kwarg():
        return 'collection'

    def _get_concept_and_mapping_ids(self, reference):
        collection_reference = CollectionReference(expression=reference)
        collection_reference.clean()
        concept_ids = map(lambda c: c.id, collection_reference.concepts)
        mapping_ids = map(lambda c: c.id, collection_reference.mappings or [])
        return {'concept_ids': concept_ids, 'mapping_ids': mapping_ids}

    def _reduce_func(self, start, current):
        new_current = self._get_concept_and_mapping_ids(current)
        start['concept_ids'] += new_current['concept_ids']
        start['mapping_ids'] += new_current['mapping_ids']
        return start

    def delete(self):
        CollectionVersion.objects.filter(versioned_object_id=self.id).delete()
        super(Collection, self).delete()

    def delete_references(self, references):
        self.expressions = []
        children_to_reduce = {'concept_ids': [], 'mapping_ids': []}
        if len(references) > 0:
            head = CollectionVersion.get_head_of(self)
            children_to_reduce = reduce(self._reduce_func, references, children_to_reduce)
            head.concepts = list(set(head.concepts) - set(children_to_reduce['concept_ids']))
            head.mappings = list(set(head.mappings) - set(children_to_reduce['mapping_ids']))
            head.references = filter(lambda ref: ref.expression not in references, head.references)
            self.references = head.references
            head.full_clean()
            head.save()
            self.full_clean()
            self.save()
        return [children_to_reduce['concept_ids'], children_to_reduce['mapping_ids']]

    def current_references(self):
        return map(lambda ref: ref.expression, self.references)

    def get_owner_type(self, owner):
        collections_url_part = owner.collections_url.split('/')[1]
        return 'user' if collections_url_part == 'users' else 'org'


COLLECTION_VERSION_TYPE = "Collection Version"


class CollectionReference(models.Model):
    expression = models.TextField()
    concepts = None
    mappings = None
    original_expression = None

    def clean(self):
        self.original_expression = str(self.expression)
        concept_klass, mapping_klass = self._resource_klasses()
        self.create_entities_from_expressions(concept_klass, mapping_klass)

        if CollectionReference.version_specified(self.expression):
            return

        self.add_concept_version_ids()
        self.add_mapping_version_ids()

    def create_entities_from_expressions(self, concept_klass, mapping_klass):
        self.concepts = concept_klass.objects.filter(uri=self.expression)
        if not self.concepts:
            self.mappings = mapping_klass.objects.filter(uri=self.expression)
            if not self.mappings:
                raise ValidationError({'detail': ['Expression specified is not valid.']})

    def add_mapping_version_ids(self):
        if not self.mappings:
            return

        self.expression += '{}/'.format(self.mappings[0].get_latest_version.mnemonic)
        self.mappings = MappingVersion.objects.filter(uri=self.expression)

    def add_concept_version_ids(self):
        if len(self.concepts) < 1:
            return

        self.expression += '{}/'.format(self.concepts[0].get_latest_version.id)
        self.concepts = ConceptVersion.objects.filter(uri=self.expression)

    @classmethod
    def version_specified(cls, expression):
        number_of_parts_with_version = 9
        return len(expression.split('/')) == number_of_parts_with_version

    def _resource_klasses(self):
        expression_parts_count = len(compact(self.expression.split('/')))
        if expression_parts_count == 6:
            return [Concept, Mapping]
        elif expression_parts_count == 7:
            return [ConceptVersion, MappingVersion]
        else:
            raise ValidationError({'detail': ['Expression specified is not valid.']})

    @property
    def reference_type(self):
        return self.expression.split('/')[5]

    @staticmethod
    def diff(ctx, _from):
        prev_expressions = map(lambda r: r.expression, _from)
        return filter(lambda ref: ref.expression not in prev_expressions, ctx)


class CollectionVersion(ConceptContainerVersionModel):
    references = ListField(EmbeddedModelField('CollectionReference'))
    collection_type = models.TextField(blank=True)
    concepts = ListField()
    mappings = ListField()
    retired = models.BooleanField(default=False)
    active_concepts = models.IntegerField(default=0)
    active_mappings = models.IntegerField(default=0)
    _ocl_processing = models.BooleanField(default=False)
    collection_snapshot = DictField(null=True, blank=True)
    custom_validation_schema = models.TextField(blank=True, null=True)

    def fill_data_for_reference(self, a_reference):
        if a_reference.concepts:
            self.concepts = self.concepts + list([concept.id for concept in a_reference.concepts])
        if a_reference.mappings:
            self.mappings = self.mappings + list([mapping.id for mapping in a_reference.mappings])
        self.references.append(a_reference)

    def seed_concepts(self):
        self._seed_resources('concepts', ConceptVersion)

    def seed_mappings(self):
        self._seed_resources('mappings', MappingVersion)

    def _seed_resources(self, resource_type, resource_klass):
        seed_mappings_from = self.head_sibling()
        if seed_mappings_from:
            resources = list(getattr(seed_mappings_from, resource_type))
            result = list()

            for resource_id in resources:
                resource_latest_version = resource_klass.get_latest_version_by_id(resource_id)
                if resource_latest_version:
                    result.append(resource_latest_version.id)
                else:
                    result.append(resource_id)

            setattr(self, resource_type, result)

    def seed_references(self):
        seed_references_from = self.head_sibling()
        if seed_references_from:
            self.references = list(seed_references_from.references)

    def get_export_key(self):
        bucket = S3ConnectionFactory.get_export_bucket()
        return bucket.get_key(self.export_path)

    def has_export(self):
        return bool(self.get_export_key())

    @property
    def export_path(self):
        last_update = self.last_child_update.strftime('%Y%m%d%H%M%S')
        collection = self.versioned_object
        return "%s/%s_%s.%s.tgz" % (collection.owner_name, collection.mnemonic, self.mnemonic, last_update)

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

    def head_sibling(self):
        return CollectionVersion.objects.get(mnemonic=HEAD, versioned_object_id=self.versioned_object_id)

    @classmethod
    def persist_new(cls, obj, user=None, **kwargs):
        obj.is_active = True
        if user:
            obj.created_by = user
            obj.updated_by = user
        kwargs['seed_concepts'] = True
        kwargs['seed_mappings'] = True
        kwargs['seed_references'] = True
        return cls.persist_changes(obj, **kwargs)

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        col_reference = kwargs.pop('col_reference', False)
        if col_reference:
            obj.fill_data_for_reference(col_reference)
        return super(CollectionVersion, cls).persist_changes(obj, **kwargs)

    def update_version_data(self, obj=None):
        if obj:
            self.description = obj.description
        else:
            try:
                obj = self.head_sibling()
            except Exception as e:
                obj = None

        if obj:
            self.name = obj.name
            self.full_name = obj.full_name
            self.website = obj.website
            self.public_access = obj.public_access
            self.collection_type = obj.collection_type
            self.supported_locales = obj.supported_locales
            self.default_locale = obj.default_locale
            self.external_id = obj.external_id

    @classmethod
    def get_head(self, id):
        return CollectionVersion.objects.get(mnemonic=HEAD, versioned_object_id=id)

    @property
    def resource_type(self):
        return COLLECTION_VERSION_TYPE

    @classmethod
    def for_base_object(cls, collection, label, previous_version=None, parent_version=None, released=False):
        if not Collection == type(collection):
            raise ValidationError("collection must be of type 'Collection'")
        if not collection.id:
            raise ValidationError("collection must have an Object ID.")
        if label == 'INITIAL':
            label = HEAD
        return CollectionVersion(
            mnemonic=label,
            name=collection.name,
            full_name=collection.full_name,
            collection_type=collection.collection_type,
            public_access=collection.public_access,
            default_locale=collection.default_locale,
            supported_locales=collection.supported_locales,
            website=collection.website,
            description=collection.description,
            versioned_object_id=collection.id,
            versioned_object_type=ContentType.objects.get_for_model(Collection),
            released=released,
            previous_version=previous_version,
            parent_version=parent_version,
            created_by=collection.created_by,
            updated_by=collection.updated_by,
            external_id=collection.external_id,
        )

    @staticmethod
    def is_processing(version_id):
        version = CollectionVersion.objects.get(id=version_id)
        return version._ocl_processing

    @staticmethod
    def clear_processing(version_id):
        version = CollectionVersion.objects.get(id=version_id)
        version._ocl_processing = False
        version.save()
        return version

admin.site.register(Collection)
admin.site.register(CollectionVersion)


@receiver(post_save)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return False
    for collection in Collection.objects.filter(parent_id=instance.id,
                                                parent_type=ContentType.objects.get_for_model(sender)):
        if instance.is_active != collection.is_active:
            collection.undelete() if instance.is_active else collection.soft_delete()


class CollectionReferenceUtils():
    @classmethod
    def get_all_related_mappings(cls, expressions, collection):
        all_related_mappings = []
        unversioned_mappings = concept_expressions = []

        for expression in expressions:
            if cls.is_mapping(expression):
                unversioned_mappings.append(cls.drop_version(expression))
            elif cls.is_concept(expression):
                concept_expressions.append(expression)

        for concept_expression in concept_expressions:
            ref = CollectionReference(expression=concept_expression)
            try:
                collection.validate(ref, concept_expression)
                related_mappings = cls.get_related_mappings(concept_expression, unversioned_mappings)
                all_related_mappings += related_mappings

            except Exception:
                continue

        return all_related_mappings

    @classmethod
    def get_related_mappings(cls, expression, existing_unversioned_mappings):
        mappings = []
        concept_id = cls.get_concept_id_by_version_information(expression)
        related_mappings = Concept.objects.get(id=concept_id).get_unidirectional_mappings()

        for mapping in related_mappings:
            if mapping.url not in existing_unversioned_mappings:
                mappings.append(mapping.url)

        return mappings

    @classmethod
    def get_concept_id_by_version_information(cls, expression):
        if CollectionReference.version_specified(expression):
            return ConceptVersion.objects.get(uri=expression).versioned_object_id
        else:
            return Concept.objects.get(uri=expression).id

    @classmethod
    def drop_version(cls, expression):
        expression_parts_without_version = '/'.join(expression.split('/')[0:7]) + '/'
        return expression_parts_without_version

    @classmethod
    def is_concept(cls, expression):
        return 'concepts' in expression

    @classmethod
    def is_mapping(cls, expression):
        return 'mappings' in expression