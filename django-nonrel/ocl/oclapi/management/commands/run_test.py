from django.core.management import BaseCommand
from configurations.management import execute_from_command_line


__author__ = 'Sny'


class Command(BaseCommand):
    help = 'run tests for oclapi'

    def handle(self, *args, **options):
        if len(args) == 0:
            _args = ['manage.py', 'test', 'users', 'concepts', 'orgs', 'oclapi', 'sources', 'collection', 'mappings']
        else:
            _args = ['manage.py', 'test']
            for item in args:
                _args.append(item)
        execute_from_command_line(_args)

