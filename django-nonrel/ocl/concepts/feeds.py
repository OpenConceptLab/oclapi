from django.contrib.contenttypes.models import ContentType
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from concepts.models import Concept, ConceptVersion
from oclapi.feeds import FeedFilterMixin
from orgs.models import Organization
from sources.models import Source
from users.models import UserProfile

__author__ = 'misternando'


class ConceptFeed(Feed, FeedFilterMixin):
    feed_type = Atom1Feed
    user = None
    org = None
    source = None
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
        if self.user:
            self.source = get_object_or_404(
                Source, mnemonic=source_id, parent_id=self.user.id,
                parent_type=ContentType.objects.get_for_model(UserProfile))
        else:
            self.source = get_object_or_404(
                Source, mnemonic=source_id, parent_id=self.org.id,
                parent_type=ContentType.objects.get_for_model(Organization))
        concept_id = kwargs.get('concept')
        self.updated_since = request.GET.get('updated_since', None)
        self.limit = request.GET.get('limit', None)
        return get_object_or_404(Concept, parent_id=self.source.id, mnemonic=concept_id)

    def title(self, obj):
        return "Updates to %s:%s" % (self.source.mnemonic, obj.mnemonic)

    def link(self, obj):
        return obj.url

    def description(self, obj):
        return "Updates to concept %s in source %s" % (obj.mnemonic, self.source.mnemonic)

    def items(self, obj):
        return self.filter_queryset(ConceptVersion.objects.filter(versioned_object_id=obj.id))

    def item_author_name(self, item):
        return item.version_created_by

    def item_title(self, item):
        return item.mnemonic

    def item_description(self, item):
        return item.update_comment

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return item.created_at
