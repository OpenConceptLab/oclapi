from django.contrib.contenttypes.models import ContentType
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from collection.models import Collection
from concepts.models import ConceptReference
from oclapi.utils import reverse_resource
from orgs.models import Organization
from users.models import UserProfile

__author__ = 'misternando'


class CollectionFeed(Feed):
    feed_type = Atom1Feed
    user = None
    org = None

    def get_object(self, request, *args, **kwargs):
        user_id = kwargs.get('user')
        try:
            self.user = UserProfile.objects.get(mnemonic=user_id)
        except UserProfile.DoesNotExist: pass
        org_id = kwargs.get('org')
        try:
            self.org = Organization.objects.get(mnemonic=org_id)
        except Organization.DoesNotExist: pass
        if not self.user or self.org:
            raise Http404("Collection owner does not exist")
        collection_id = kwargs.get('collection')
        if self.user:
            return get_object_or_404(Collection, mnemonic=collection_id, parent_id=self.user.id, parent_type=ContentType.objects.get_for_model(UserProfile))
        else:
            return get_object_or_404(Collection, mnemonic=collection_id, parent_id=self.user.id, parent_type=ContentType.objects.get_for_model(Organization))

    def title(self, obj):
        return "Updates to %s" % obj.mnemonic

    def link(self, obj):
        return reverse_resource(obj, 'collection-detail')

    def description(self, obj):
        return "Updates to concepts within collection %s" % obj.mnemonic

    def items(self, obj):
        return ConceptReference.objects.filter(parent_id=obj.id).order_by('-updated_at')[:30]

    def item_title(self, item):
        return item.mnemonic

    def item_description(self, item):
        return item.display_name

    def item_link(self, item):
        return reverse_resource(item, 'collection-concept-detail')

