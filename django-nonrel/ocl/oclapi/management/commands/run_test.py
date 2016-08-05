from django.core.management import BaseCommand
from configurations.management import execute_from_command_line


__author__ = 'Sny'


class Command(BaseCommand):
    """ Command to import JSON lines mapping file into OCL """
    help = 'run tests for oclapi'

    def handle(self, *args, **options):
        execute_from_command_line(['manage.py', 'test', 'users', 'concepts', 'orgs', 'oclapi', 'sources', 'collection', 'mappings'])
