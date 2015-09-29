from optparse import make_option
import logging
import os
from django.core.management import BaseCommand, CommandError
import haystack
from haystack.signals import BaseSignalProcessor
from rest_framework.authtoken.models import Token
from oclapi.permissions import HasPrivateAccess
from sources.models import Source
from cProfile import Profile

__author__ = 'misternando,paynejd'
logger = logging.getLogger('batch')


class ImportActionHelper(object):
    """ Import action constants """

    # Import action constants can be combined if multiple actions performed on a concept
    IMPORT_ACTION_NONE = 0
    IMPORT_ACTION_ADD = 0b1  # 1
    IMPORT_ACTION_UPDATE = 0b10  # 2
    IMPORT_ACTION_RETIRE = 0b100  # 4
    IMPORT_ACTION_UNRETIRE = 0b1000  # 8
    IMPORT_ACTION_DEACTIVATE = 0b10000  # 16
    IMPORT_ACTION_SKIP = 0b100000  # 32

    # Names for each action
    IMPORT_ACTION_NAMES = {
        IMPORT_ACTION_NONE: 'no action/no diff',
        IMPORT_ACTION_ADD: 'added',
        IMPORT_ACTION_UPDATE: 'updated',
        IMPORT_ACTION_RETIRE: 'retired',
        IMPORT_ACTION_UNRETIRE: 'unretired',
        IMPORT_ACTION_DEACTIVATE: 'deactivated',
        IMPORT_ACTION_SKIP: 'skipped due to error',
    }

    # Ordered list of actions useful for iterating quickly
    ORDERED_ACTION_LIST = [32, 16, 8, 4, 2, 1]

    @classmethod
    def get_action_string(cls, combined_action_value):
        """
        Returns text name of the action, where action is an integer of one or
        more of the import actions added together.
        E.g. if action = 8 + 2, returns "updated + unretired"
        """
        if combined_action_value in ImportActionHelper.IMPORT_ACTION_NAMES:
            return ImportActionHelper.IMPORT_ACTION_NAMES[combined_action_value]
        combined_action_text = ''
        for individual_action_value in ImportActionHelper.ORDERED_ACTION_LIST:
            if combined_action_value >= individual_action_value:
                if combined_action_text:
                    combined_action_text += (
                        ' + ' + ImportActionHelper.IMPORT_ACTION_NAMES[individual_action_value])
                else:
                    combined_action_text = (
                        ImportActionHelper.IMPORT_ACTION_NAMES[individual_action_value])
                combined_action_value -= individual_action_value
        return combined_action_text

    @classmethod
    def get_progress_descriptor(cls, str_import_type, current_num, total_num, action_count):
        """ Returns a string with the current counts of the import process """
        str_descriptor = '%d of %d %s -' % (str_import_type, current_num, total_num)
        for action_value, num in action_count.items():
            str_descriptor += ' %d %s,' % (num, ImportActionHelper.get_action_string(action_value))
        str_descriptor += '\n'
        return str_descriptor


class MockRequest(object):
    """ Mock request """
    method = 'POST'
    user = None

    def __init__(self, user):
        self.user = user


class ImportCommand(BaseCommand):
    """ Import Command """
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
                    help='Mongo UUID of the source into which to import concepts.'),
        make_option('--create-source-version',
                    action='store',
                    dest='new_version',
                    default=None,
                    help='Import to new version of the specified source.'),
        make_option('--retire-missing-records',
                    action='store_true',
                    dest='deactivate_old_records',
                    default=None,
                    help='Retires all concepts/mappings in the specified source that are not included in the import file.'),
        make_option('--test-only',
                    action='store_true',
                    dest='test-only',
                    default=False,
                    help='If true, describes diffs and actions that would be taken to reconcile differences without executing them.'),
        make_option('--profile',
                    action='store_true',
                    dest='profile',
                    default=False,
                    help='Compute and dislpay cProfile statistics'),
    )


    def handle(self, *args, **options):
        """ Handles the command line arguments - initiates profiling if set to true """
        if options.get('profile', False):
            profiler = Profile()
            profiler.runcall(self._handle, *args, **options)
            profiler.print_stats()
        else:
            self._handle(*args, **options)


    def _handle(self, *args, **options):
        """ Performs the actual operations """
        if len(args) != 1:
            raise CommandError('Wrong number of arguments.  (Got %s; expected 1)' % len(args))

        input_filename = args[0]
        if not os.path.exists(input_filename):
            raise CommandError('Could not find input file %s' % input_filename)

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

        # Set test status -- if true, process import without changing the underlying database
        self.test_mode = False
        if options['test-only']:
            self.test_mode = True

        permission = HasPrivateAccess()
        if not permission.has_object_permission(MockRequest(user), None, source):
            raise CommandError('User does not have permission to edit source.')

        # Get total record count
        logger.info('Import begins user %s source %s' % (user, source))
        try:
            with open(input_filename, 'rb') as input_file:
                total = sum(1 for line in input_file)
                options['total'] = total
                self.stdout.write('Importing %d record(s)...\n' % total)
                logger.info('Importing %d record(s)...' % total)
        except IOError:
            raise CommandError('Could not open input file %s' % input_filename)

        # Open the file a second time to pass to the import function
        try:
            input_file = open(input_filename, 'rb')
        except IOError:
            raise CommandError('Could not open input file %s' % input_filename)

        haystack.signal_processor = BaseSignalProcessor(haystack.connections, haystack.connection_router)

        # Perform the import
        self.do_import(user, source, input_file, options)
        logger.info('Import finished')

    def do_import(self, user, source, input_file, options):
        """ Should be overwritten to actually perform the import """
        pass
