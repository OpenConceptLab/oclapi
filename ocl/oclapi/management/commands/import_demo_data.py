import sys

from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.core.management.base import OutputWrapper

from concepts.importer import ConceptsImporter
from mappings.importer import MappingsImporter

from orgs.models import Organization
from sources.models import Source
from users.models import UserProfile


class Command(BaseCommand):
    help = 'import demo data'

    def handle(self, *args, **options):
        user = self.create_admin_user()

        org = self.create_organization(user, 'CIEL')

        source = self.create_source(user, org, 'CIEL')

        demo_file = open('./demo-data/ciel_20180601_concepts_2k.json', 'rb')
        importer = ConceptsImporter(source, demo_file, user, OutputWrapper(sys.stdout), OutputWrapper(sys.stderr), save_validation_errors=False)
        importer.import_concepts(**options)

        demo_file = open('./demo-data/ciel_20180601_mappings_2k.json', 'rb')
        importer = MappingsImporter(source, demo_file, OutputWrapper(sys.stdout), OutputWrapper(sys.stderr), user)
        importer.import_mappings(**options)

    def create_admin_user(self):
        admin_user = User.objects.filter(username='admin')
        if not admin_user.exists():
            admin_user = User.objects.create_user('admin', 'admin@openconceptlab.org', password='Admin123')
            UserProfile.objects.create(user=admin_user, hashed_password=admin_user.password, mnemonic='admin')
        else:
            admin_user = admin_user.get()

        return admin_user

    def create_organization(self, user, name):
        if Organization.objects.filter(mnemonic=name).count() < 1:
            org = Organization(mnemonic=name, name=name, company=name, members=[user.id],
                               created_by='root', updated_by='root')
            org.full_clean()
            org.save()
        else:
            org = Organization.objects.get(mnemonic=name)
        return org

    def create_source(self, user, org, name):
        kwargs = {
            'parent_resource': org
        }

        if Source.objects.filter(parent_id=org.id, mnemonic=name).count() < 1:
            source = Source(name=name, mnemonic=name, full_name=name, parent=org,
                            created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
            Source.persist_new(source, user, **kwargs)
        else:
            source = Source.objects.get(parent_id=org.id, mnemonic=name)

        return source