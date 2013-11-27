from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from oclapi.models import VERSION_TYPE

__author__ = 'misternando'


class ConceptContainerMixin(object):

    @property
    def num_versions(self):
        return self.get_version_model().objects.filter(versioned_object_id=self.id).count()

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource')
        user = kwargs.pop('owner')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if cls.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            errors['mnemonic'] = '%s with mnemonic %s already exists for parent resource %s.' % (cls, mnemonic, parent_resource.mnemonic)
            return errors
        obj.parent = parent_resource
        obj.owner = user
        with transaction.commit_on_success():
            obj.save(**kwargs)
            version_model = cls.get_version_model()
            version = version_model.for_base_object(obj, 'INITIAL')
            version.released = True
            version.save()
        return errors

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        matching_sources = cls.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic)
        if matching_sources.exists():
            if matching_sources[0] != obj:
                errors['mnemonic'] = '%s with mnemonic %s already exists for parent resource %s.' % (cls, mnemonic, parent_resource.mnemonic)
                return errors
        obj.save(**kwargs)
        return errors


class ConceptContainerVersionMixin(object):

    @classmethod
    def resource_type(cls):
        return VERSION_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'version'

    @classmethod
    def for_base_object(cls, obj, label, previous_version=None, parent_version=None):
        pass

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        versioned_object = kwargs.get('versioned_object', None)
        if versioned_object is None:
            errors['non_field_errors'] = ['Must specify a versioned object.']
            return errors
        if cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj.mnemonic).exists():
            errors['mnemonic'] = ["Version with mnemonic %s already exists for source %s." % (obj.mnemonic, versioned_object.mnemonic)]
            return errors
        kwargs['seed_concepts'] = True
        return cls.persist_changes(obj, **kwargs)

    @classmethod
    def persist_changes(cls, obj, **kwargs):
        errors = dict()
        versioned_object = kwargs.pop('versioned_object')
        if versioned_object is None:
            errors['non_field_errors'] = ['Must specify a versioned object.']
            return errors
        if obj._previous_version_mnemonic:
            previous_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._previous_version_mnemonic)
            if not previous_version_queryset.exists():
                errors['previousVersion'] = ["Previous version %s does not exist." % obj._previous_version_mnemonic]
            elif obj.mnemonic == obj._previous_version_mnemonic:
                errors['previousVersion'] = ["Previous version cannot be the same as current version."]
            else:
                obj.previous_version = previous_version_queryset[0]
                del obj._previous_version_mnemonic
        if obj._parent_version_mnemonic:
            parent_version_queryset = cls.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._parent_version_mnemonic)
            if not parent_version_queryset.exists():
                errors['parentVersion'] = ["Parent version %s does not exist." % obj._parent_version_mnemonic]
            elif obj.mnemonic == obj._parent_version_mnemonic:
                errors['parentVersion'] = ["Parent version cannot be the same as current version."]
            else:
                obj.parent_version = parent_version_queryset[0]
                del obj._parent_version_mnemonic
        if errors:
            return errors
        seed_concepts = kwargs.pop('seed_concepts', False)
        if seed_concepts:
            seed_concepts_from = obj.previous_version or obj.parent_version
            if seed_concepts_from:
                obj.concepts = list(seed_concepts_from.concepts)
        with transaction.commit_on_success():
            obj.versioned_object = versioned_object
            release_version = obj._release_version
            del obj._release_version
            error_cause = 'updating version'
            try:
                obj.save(**kwargs)
                if release_version:
                    error_cause = 'updating released statuses'
                    for v in cls.objects.filter(versioned_object_id=versioned_object.id, released=True).exclude(mnemonic=obj.mnemonic):
                        v.released = False
                        v.save()
            except Exception:
                errors['non_field_errors'] = ["Encountered an error while %s." % error_cause]
        return errors


