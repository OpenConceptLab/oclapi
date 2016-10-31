import sys
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.core.management.base import OutputWrapper

from concepts.importer import ConceptsImporter
from orgs.models import Organization
from sources.models import Source


class Command(BaseCommand):
    help = 'import lookup values'

    def handle(self, *args, **options):
        user = User.objects.filter(username='root').get()

        org = self.create_organization(user)

        sources = self.create_sources(org, user)

        importer_confs = [
            {'source': sources['Classes'], 'file': "./concept_classes.json"},
            {'source': sources['Locales'], 'file': "./locales.json"},
            {'source': sources['Datatypes'], 'file': "./datatypes_fixed.json"},
            {'source': sources['NameTypes'], 'file': "./nametypes_fixed.json"},
            {'source': sources['DescriptionTypes'], 'file': "./description_types.json"}
        ]

        for conf in importer_confs:
            file = open(conf['file'], 'rb')
            source = conf['source']

            importer = ConceptsImporter(source, file, user, OutputWrapper(sys.stdout), OutputWrapper(sys.stderr))
            importer.import_concepts(**options)

    def create_organization(self, user):
        org = None
        if Organization.objects.filter(mnemonic='OCL').count() < 1:
            org = Organization(mnemonic='OCL', name='Open Concept Lab', company="Open Concept Lab", members=[user.id],
                               created_by='root', updated_by='root')
            org.full_clean()
            org.save()
        else:
            org = Organization.objects.get(mnemonic='OCL')
        return org

    def create_sources(self, org, user):
        sources = dict()
        source = None

        kwargs = {
            'parent_resource': org
        }

        if Source.objects.filter(parent_id=org.id, mnemonic='Locales').count() < 1:
            source = Source(name='Locales', mnemonic='Locales', full_name='Locales', parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)

        else:
            source = Source.objects.get(parent_id=org.id, mnemonic='Locales')
        sources['Locales'] = source

        if Source.objects.filter(parent_id=org.id, mnemonic='Classes').count() < 1:
            source = Source(name='Classes', mnemonic='Classes', full_name='Classes', parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)

        else:
            source = Source.objects.get(parent_id=org.id, mnemonic='Classes')
        sources['Classes'] = source

        if Source.objects.filter(parent_id=org.id, mnemonic='Datatypes').count() < 1:
            source = Source(name='Datatypes', mnemonic='Datatypes', full_name='Datatypes', parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)

        else:
            source = Source.objects.get(parent_id=org.id, mnemonic='Datatypes')
        sources['Datatypes'] = source

        if Source.objects.filter(parent_id=org.id, mnemonic='DescriptionTypes').count() < 1:
            source = Source(name='DescriptionTypes', mnemonic='DescriptionTypes', full_name='DescriptionTypes',
                            parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)

        else:
            source = Source.objects.get(parent_id=org.id, mnemonic='DescriptionTypes')
        sources['DescriptionTypes'] = source

        if Source.objects.filter(parent_id=org.id, mnemonic='NameTypes').count() < 1:
            source = Source(name='NameTypes', mnemonic='NameTypes', full_name='NameTypes', parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)

        else:
            source = Source.objects.get(parent_id=org.id, mnemonic='NameTypes')
        sources['NameTypes'] = source

        print sources

        return sources
