from optparse import make_option
import os.path
from django.core.management import BaseCommand, CommandError
from rest_framework.authtoken.models import Token
from mappings.importer import MappingsImporter
from sources.models import Source

__author__ = 'misternando'


class Command(BaseCommand):
    args = '--token=[token] --source=[source ID] [mappings input file]'
    help = 'Import mappings from a JSON file into a source'
    option_list = BaseCommand.option_list + (
        make_option('--token',
                    action='store',
                    dest='token',
                    default=None,
                    help='Token used to authenticate user with access to this source.'),
        make_option('--source',
                    action='store',
                    dest='source_id',
                    default=None,
                    help='Import mappings to this source.'),
        make_option('--create-source-version',
                    action='store',
                    dest='new_version',
                    default=None,
                    help='Import mappings to new version of the specified source.'),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Wrong number of arguments.  (Got %s; expected 1)' % len(args))

        input_file = args[0]
        if not os.path.exists(input_file):
            raise CommandError('Could not find input file %s' % input_file)

        source_id = options['source_id']
        if not source_id:
            raise CommandError('Must specify a source.')

        token = options['token']
        if not token:
            raise CommandError('Must specify authentication token.')

        try:
            source = Source.objects.get(id=source_id)
        except Source.DoesNotExist:
            raise CommandError('Could not find source with id=%s' % source_id)

        try:
            auth_token = Token.objects.get(key=token)
            user = auth_token.user
        except Token.DoesNotExist:
            raise CommandError('Invalid token.')

        try:
            input_file = open(input_file, 'rb')
            # get total record count
            total = sum(1 for line in input_file)
            input_file.seek(0)
            self.stdout.write('Adding/updating %d new mappings...\n' % total)
        except IOError:
            raise CommandError('Could not open input file %s' % input_file)

        importer = MappingsImporter(source, input_file, self.stdout, self.stderr, user)
        importer.import_mappings(options['new_version'])
