from oclapi.filters import HaystackSearchFilter
from collection.models import Collection, CollectionVersion

LATEST = 'latest'

__author__ = 'misternando'


class ConceptSearchFilter(HaystackSearchFilter):
    def get_filters(self, request, view):
        filters = super(ConceptSearchFilter, self).get_filters(request, view)
        if view.updated_since:
            filters.update({'last_update__gte': view.updated_since})
        if not view.include_retired:
            filters.update({'retired': False})
        return filters


class PublicConceptsSearchFilter(ConceptSearchFilter):

    def get_filters(self, request, view):
        filters = super(PublicConceptsSearchFilter, self).get_filters(request, view)
        filters.update({'public_can_view': True})
        return filters


class LimitSourceVersionFilter(ConceptSearchFilter):

    def get_filters(self, request, view):
        filters = super(LimitSourceVersionFilter, self).get_filters(request, view)
        filters.update({'source_version': view.parent_resource_version.id})
        return filters


class LimitCollectionVersionFilter(ConceptSearchFilter):
    def get_filters(self, request, view):
        filters = super(LimitCollectionVersionFilter, self).get_filters(request, view)
        if 'collection' in view.kwargs:
            owner = view.get_owner()
            collection = Collection.objects.get(parent_id=owner.id, mnemonic=view.kwargs['collection'])
            if 'version' in view.kwargs and view.kwargs['version'] != 'HEAD':
                if view.kwargs['version'] == LATEST:
                    collection_version = CollectionVersion.get_latest_released_version_of(collection)
                else:
                    collection_version = CollectionVersion.objects.get(versioned_object_id=collection.id, mnemonic=view.kwargs['version'])
                filters.update({'collection_version': collection_version.id})
            else:
                collection_version = CollectionVersion.objects.get(versioned_object_id=collection.id, mnemonic='HEAD')
                filters.update({'collection_version': collection_version.id})
        return filters
