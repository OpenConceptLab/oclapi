import logging
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from djangotoolbox.fields import ListField
from collection.models import Collection
from oclapi.models import BaseResourceModel
from sources.models import Source
from oclapi.utils import lazyproperty

USER_OBJECT_TYPE = 'User'
ORG_OBJECT_TYPE = 'Organization'

logger = logging.getLogger('oclapi')

class UserProfile(BaseResourceModel):
    user = models.OneToOneField(User)
    hashed_password = models.TextField(null=True, blank=True)
    full_name = models.TextField(null=True, blank=True)
    company = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    preferred_locale = models.TextField(null=True, blank=True)
    organizations = ListField()

    def __unicode__(self):
        return self.mnemonic

    def soft_delete(self):
        if self.user.is_active:
            self.user.is_active = False
            self.user.save()
        super(UserProfile, self).soft_delete()

    def undelete(self):
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save()
        super(UserProfile, self).undelete()

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

    @lazyproperty
    def public_collections(self):
        return Collection.objects.filter(parent_id=self.id).count()

    @lazyproperty
    def public_sources(self):
        return Source.objects.filter(parent_id=self.id).count()

    @property
    def organizations_url(self):
        return reverse('userprofile-orgs', kwargs={'user': self.mnemonic})

    @property
    def sources_url(self):
        return reverse('source-list', kwargs={'user': self.mnemonic})

    @property
    def collections_url(self):
        return reverse('collection-list', kwargs={'user': self.mnemonic})

    def is_admin_for(self, concept_container):
        if concept_container.owner_type == UserProfile.resource_type():
            if concept_container.owner == self:
                return True
        else:
            for org in self.organizations:
                if org == concept_container.owner:
                    return True
        return False

    @property
    def num_stars(self):
        return 0

    @staticmethod
    def get_url_kwarg():
        return 'user'


admin.site.register(UserProfile)
