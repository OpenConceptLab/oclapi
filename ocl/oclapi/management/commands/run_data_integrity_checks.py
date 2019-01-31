from django.core.management import BaseCommand
from tasks import data_integrity_checks

class Command(BaseCommand):
    help = 'Run data integrity checks'

    def handle(self, *args, **options):
        pass #data_integrity_checks.delay()
