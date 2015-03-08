from optparse import make_option
import os
from django.core.management import BaseCommand, CommandError
import haystack
from haystack.signals import BaseSignalProcessor
from rest_framework.authtoken.models import Token
from oclapi.permissions import HasPrivateAccess
from sources.models import Source

__author__ = 'misternando'


class MockRequest(object):
    method = 'POST'
    user = None

    def __init__(self, user):
        self.user = user


class ImportCommand(BaseCommand):
    args = '--token=[token] --source=[source ID] [input file]'
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
                    help='Import to this source.'),
        make_option('--create-source-version',
                    action='store',
                    dest='new_version',
                    default=None,
                    help='Import to new version of the specified source.'),
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

        permission = HasPrivateAccess()
        if not permission.has_object_permission(MockRequest(user), None, source):
            raise CommandError('User does not have permission to edit source.')

        try:
            input_file = open(input_file, 'rb')
            # get total record count
            total = sum(1 for line in input_file)
            options['total'] = total
            input_file.seek(0)
            self.stdout.write('Adding/updating %d new records...\n' % total)
        except IOError:
            raise CommandError('Could not open input file %s' % input_file)

        haystack.signal_processor = BaseSignalProcessor(haystack.connections, haystack.connection_router)
        self.do_import(user, source, input_file, options)

    def do_import(self, user, source, input_file, options):
        pass
