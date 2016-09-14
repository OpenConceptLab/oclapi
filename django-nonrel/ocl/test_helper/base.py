from collection.models import CollectionVersion, Collection
from concepts.models import Concept, ConceptVersion, LocalizedText
from orgs.models import Organization
from sources.models import Source, SourceVersion
from users.models import UserProfile
from mappings.models import Mapping, MappingVersion
from django.contrib.auth.models import User
from django.test import TestCase


class OclApiBaseTestCase(TestCase):
    def tearDown(self):
        User.objects.filter().delete()
        UserProfile.objects.filter().delete()
        Organization.objects.filter().delete()
        Source.objects.filter().delete()
        SourceVersion.objects.filter().delete()
        LocalizedText.objects.filter().delete()
        Concept.objects.filter().delete()
        ConceptVersion.objects.filter().delete()
        Collection.objects.filter().delete()
        CollectionVersion.objects.filter().delete()
        Mapping.objects.filter().delete()
        MappingVersion.objects.filter().delete()