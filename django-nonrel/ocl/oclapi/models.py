from django.db import models
from uuidfield import UUIDField


class BaseModel(models.Model):
    uuid = UUIDField(auto=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
