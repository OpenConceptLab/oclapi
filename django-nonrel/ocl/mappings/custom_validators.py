from django.core.exceptions import ValidationError


class OpenMRSMappingValidator:
    def __init__(self, mapping):
        self.mapping = mapping

    def validate(self):
        self.pair_must_be_unique()

    def pair_must_be_unique(self):
        from mappings.models import Mapping

        intersection = Mapping.objects.filter(from_concept=self.mapping.from_concept,
                                              to_concept=self.mapping.to_concept, is_active=True, retired=False).count()

        if intersection:
            raise ValidationError("Custom validation rules require only one Mapping to exist between two Concepts")
