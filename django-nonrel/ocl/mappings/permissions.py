from rest_framework.permissions import BasePermission

from ..oclapi.permissions import CanViewConceptDictionary, CanEditConceptDictionary


__author__ = 'misternando'


class CanAccessParentSource(BasePermission):
    dictionary_permission_class = None

    def has_object_permission(self, request, view, obj):
        source = obj.parent
        dictionary = source.parent
        dictionary_permission = self.dictionary_permission_class()
        return dictionary_permission.has_object_permission(request, view, dictionary)


class CanViewParentSource(CanAccessParentSource):
    dictionary_permission_class = CanViewConceptDictionary


class CanEditParentSource(CanAccessParentSource):
    dictionary_permission_class = CanEditConceptDictionary
