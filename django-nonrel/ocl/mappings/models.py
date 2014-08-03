from django.core.exceptions import ValidationError
from django.db import models
from concepts.models import Concept
from oclapi.models import SubResourceBaseModel


class Mapping(SubResourceBaseModel):
    map_type = models.TextField()
    to_concept = models.ForeignKey(Concept, null=True, blank=True)
    to_source_url = models.URLField(null=True, blank=True)
    to_concept_name = models.TextField(null=True, blank=True)
    to_concept_code = models.TextField(null=True, blank=True)

    def clean(self, exclude=None):
        if not (self.to_concept or self.to_source_url or self.to_concept_name or self.to_concept_code):
            raise ValidationError("Must specify either 'to_concept' or 'to_source_url', 'to_concept_name' & 'to_concept_code'")
        if self.to_concept and self.to_source_url and self.to_concept_name and self.to_concept_code:
            raise ValidationError("Must specify one of 'to_concept' or 'to_source_url', 'to_concept_name' & 'to_concept_code'.  Cannot specify both.")

    @classmethod
    def persist_new(cls, obj, **kwargs):
        errors = dict()
        non_field_errors = []
        owner = kwargs.pop('owner', None)
        if owner is None:
            non_field_errors.append('Must specify an owner')
        obj.owner = owner
        parent_resource = kwargs.pop('parent_resource', None)
        if parent_resource is None:
            non_field_errors.append('Must specify a parent resource (the "from" concept).')
        obj.parent = parent_resource
        if non_field_errors:
            errors['non_field_errors'] = non_field_errors
            return errors
        to_concept = obj.to_concept
        if to_concept:
            if cls.objects.filter(owner=owner, parent_id=parent_resource.id, to_concept=to_concept).exists():
                errors['non_field_errors'] = ["Mapping already exists from %s to %s" % (parent_resource, to_concept)]
                return errors
        persisted = False
        try:
            obj.save(**kwargs)
            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ["Failed to persist mapping."]
        return errors


