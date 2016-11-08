from optparse import make_option
from django.core.management import BaseCommand
from configurations.management import execute_from_command_line


__author__ = 'Sny'


class Command(BaseCommand):
    help = 'run tests for oclapi'

    option_list = BaseCommand.option_list + (
        make_option('--failfast',
                    action='store_true',
                    dest='failfast',
                    default=None,
                    help='Fail fast'),)

    def handle(self, *args, **options):
        if len(args) == 0:
            _args = ['manage.py', 'test', 'users', 'concepts', 'orgs', 'oclapi', 'sources', 'collection', 'mappings']
        else:
            _args = ['manage.py', 'test']

        for item in args:
            print("Appending argument: {0}".format(item))
            _args.append(item)

        if options["failfast"]:
            _args.append("--failfast")

        execute_from_command_line(_args)

