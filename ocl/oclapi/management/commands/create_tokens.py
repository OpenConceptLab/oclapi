from optparse import make_option
import os.path
import requests
import json

from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from rest_framework.authtoken.models import Token
from users.models import UserProfile
from orgs.models import Organization

class Command(BaseCommand):
    help = 'Create initial user data for new installation, output the tokens required for the web.'
    option_list = BaseCommand.option_list + (
        make_option('--password',
                    action='store',
                    dest='pwd',
                    default=None,
                    help='Password for root user.'),
        make_option('--test',
                    action='store_true',
                    dest='test_mode',
                    default=False,
                    help='Test mode. Do not update database.'),
        make_option('--create',
                    action='store_true',
                    dest='create_mode',
                    default=False,
                    help='Create root user.'),
        make_option('--token',
                    action='store',
                    dest='token',
                    default=None,
                    help='Set root user token.')
    )

    def print_users(self):
        print 'Django users...'
        for n,u in enumerate(User.objects.all(), start=1):
            print 'Django User %d -----' % n
            print 'user id:', u.id
            print 'user name:', u.username
            print 'is staff:', u.is_staff
            print 'is superuser:', u.is_superuser


        print 'API users...'
        for n, u in enumerate(UserProfile.objects.all(), start=1):
            print 'API User %d -----' % n
            print 'user id:', u.id
            print 'mnemonic:', u.mnemonic
            print 'name:', u.name


    def print_tokens(self):
        """ Just print out the tokens, in a form that easily put
            in a shell script.
        """

        for t in Token.objects.all():
            res = User.objects.filter(id=t.user_id)
            if len(res) == 1:
                un = res[0].username
            else:
                un = 'n/a'
            if un == 'admin':
                print "export OCL_API_TOKEN='%s'" % t.key
            if un == 'anonymous':
                print "export OCL_ANON_API_TOKEN='%s'" % t.key


    def handle(self, *args, **options):

        create_mode = options['create_mode']
        pwd = options['pwd']
        token = options['token']

        if create_mode:
            if pwd is None:
                raise CommandError('--password is required.')
            
            superusers = User.objects.filter(username='root')

            if not superusers:
                UserProfile.objects.create(
                    user=User.objects.create_superuser('root', 'root@openconceptlab.org', password=pwd),
                    organizations=map(lambda o: o.id, Organization.objects.filter(created_by='root')),
                    mnemonic='root')
                superusers = User.objects.filter(username='root')

            superuser = superusers[0]

            superuser.set_password(pwd)
            superuser.save()

            print "OCL_API_TOKEN='%s'" % token

            if token:
                Token.objects.filter(user=superuser).delete()
                Token.objects.create(user=superuser, key=token)

        else:
            self.print_tokens()

