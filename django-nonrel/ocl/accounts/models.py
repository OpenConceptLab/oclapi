from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from oclapi.models import BaseModel


class UserProfile(BaseModel):
    user = models.OneToOneField(User)
    company = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    preferred_locale = models.CharField(max_length=20, null=True, blank=True)

    def get_uuid(self):
        return str(self.uuid)

    def get_full_name(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)


admin.site.register(UserProfile)


