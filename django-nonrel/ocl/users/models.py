from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from djangotoolbox.fields import ListField
from oclapi.models import BaseResourceModel
from sources.models import Source

USER_OBJECT_TYPE = 'User'
ORG_OBJECT_TYPE = 'Organization'


class UserProfile(BaseResourceModel):
    user = models.OneToOneField(User)
    full_name = models.TextField(null=True, blank=True)
    company = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    preferred_locale = models.TextField(null=True, blank=True)
    organizations = ListField()

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        return self.full_name or "%s %s" % (self.user.first_name, self.user.last_name)

    @classmethod
    def resource_type(cls):
        return USER_OBJECT_TYPE

    @property
    def username(self):
        return self.mnemonic or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def orgs(self):
        return len(self.organizations)

    @property
    def public_sources(self):
        return Source.objects.filter(parent_id=self.id).count()

    @staticmethod
    def get_url_kwarg():
        return 'user'


admin.site.register(UserProfile)
