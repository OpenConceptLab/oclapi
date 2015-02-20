from optparse import make_option
import os.path
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from mappings.importer import MappingsImporter
from sources.models import Source

__author__ = 'misternando'


class Command(BaseCommand):
    args = '[source_id] [mappings input file]'
    help = 'Import mappings from a JSON file into a source'
    option_list = BaseCommand.option_list + (
        make_option('--create-source-version',
                    action='store',
                    dest='new_version',
                    default=None,
                    help='Import mappings to new version of source.'),
    )

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Wrong number of arguments.  (Got %s; expected 2)' % len(args))

        source_id = args[0]
        try:
            source = Source.objects.get(id=source_id)
        except Source.DoesNotExist:
            raise CommandError('Could not find source with id=%s' % source_id)

        input_file = args[1]
        if not os.path.exists(input_file):
            raise CommandError('Could not find input file %s' % input_file)

        try:
            input_file = open(input_file, 'rb')
            # get total record count
            total = sum(1 for line in input_file)
            input_file.seek(0)
            self.stdout.write('Adding/updating %d new mappings...\n' % total)
        except IOError:
            raise CommandError('Could not open input file %s' % input_file)

        user = None
        for u in User.objects.filter(is_staff=True):
            try:
                u.get_profile()
                user = u
                break
            except: pass
        importer = MappingsImporter(source, input_file, self.stdout, self.stderr, user)
        importer.import_mappings(options['new_version'])
