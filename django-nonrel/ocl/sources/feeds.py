from django.contrib.contenttypes.models import ContentType
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from concepts.models import ConceptVersion, Concept
from oclapi.feeds import FeedFilterMixin
from orgs.models import Organization
from sources.models import Source
from users.models import UserProfile

__author__ = 'misternando'


class SourceFeed(Feed, FeedFilterMixin):
    feed_type = Atom1Feed
    user = None
    org = None
    updated_since = None
    limit = 0

    def get_object(self, request, *args, **kwargs):
        user_id = kwargs.get('user')
        try:
            self.user = UserProfile.objects.get(mnemonic=user_id)
        except UserProfile.DoesNotExist: pass
        org_id = kwargs.get('org')
        try:
            self.org = Organization.objects.get(mnemonic=org_id)
        except Organization.DoesNotExist: pass
        if not (self.user or self.org):
            raise Http404("Source owner does not exist")
        source_id = kwargs.get('source')
        self.updated_since = request.GET.get('updated_since', None)
        self.limit = request.GET.get('limit', None)
        if self.user:
            return get_object_or_404(Source, mnemonic=source_id, parent_id=self.user.id, parent_type=ContentType.objects.get_for_model(UserProfile))
        else:
            return get_object_or_404(Source, mnemonic=source_id, parent_id=self.org.id, parent_type=ContentType.objects.get_for_model(Organization))

    def title(self, obj):
        return "Updates to %s" % obj.mnemonic

    def link(self, obj):
        return obj.url

    def description(self, obj):
        return "Updates to concepts within source %s" % obj.mnemonic

    def items(self, obj):
        return self.filter_queryset(Concept.objects.filter(parent_id=obj.id))

    def item_title(self, item):
        return item.mnemonic

    def item_description(self, item):
        item = ConceptVersion.get_latest_version_of(item)
        return item.update_comment

    def item_link(self, item):
        return item.url

