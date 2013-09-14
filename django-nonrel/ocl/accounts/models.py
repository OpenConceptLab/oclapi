from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from oclapi.models import BaseModel

USER_OBJECT_TYPE = 'User'
ORG_OBJECT_TYPE = 'Organization'


class UserProfile(BaseModel):
    user = models.OneToOneField(User)
    full_name = models.TextField(null=True, blank=True)
    company = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    preferred_locale = models.CharField(max_length=20, null=True, blank=True)

    @property
    def name(self):
        return self.full_name or "%s %s" % (self.user.first_name, self.user.last_name)

    @property
    def type(self):
        return USER_OBJECT_TYPE

    @property
    def username(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email

    @classmethod
    @receiver(post_save, sender=User)
    def create_auth_token(sender, instance=None, created=False, **kwargs):
        if created:
            Token.objects.create(user=instance)


class Organization(BaseModel, Group):
    display_name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)

    @property
    def name(self):
        return self.display_name or self.name

    @property
    def type(self):
        return ORG_OBJECT_TYPE


admin.site.register(UserProfile)
admin.site.register(Organization)

