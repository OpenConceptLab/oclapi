from oclapi.filters import HaystackSearchFilter, SimpleHaystackSearchFilter
from collection.models import Collection, CollectionVersion
LATEST = 'latest'

__author__ = 'misternando'


class PublicMappingsSearchFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicMappingsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        return filters


class SourceRestrictedMappingsFilter(HaystackSearchFilter):

    def get_filters(self, request, view):
        filters = super(SourceRestrictedMappingsFilter, self).get_filters(request, view)
        if 'collection' not in view.kwargs:
            filters.update({'source_version': view.parent_resource_version.id})
        return filters


class CollectionRestrictedMappingFilter(SimpleHaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(CollectionRestrictedMappingFilter, self).get_filters(request, view)
        if 'collection' in view.kwargs:
            owner = view.get_owner()
            collection = Collection.objects.get(parent_id=owner.id, mnemonic=view.kwargs['collection'])
            if 'version' in view.kwargs:
                if view.kwargs['version'] == LATEST:
                    collection_version = CollectionVersion.get_latest_released_version_of(collection)
                else:
                    collection_version = CollectionVersion.objects.get(versioned_object_id=collection.id, mnemonic=view.kwargs['version'])

                filters.update({'collection_version': collection_version.id})
            else:
                filters.update({'collection': collection.id})
        return filters
