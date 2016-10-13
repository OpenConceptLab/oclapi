from django.db import models


class SelectionAttributesBaseModel(models.Model):
    name = models.TextField()

    class Meta:
        abstract = True


class ConceptClass(SelectionAttributesBaseModel):
    pass


class ConceptDataType(SelectionAttributesBaseModel):
    pass


class NameLocale(SelectionAttributesBaseModel):
    code = models.TextField()