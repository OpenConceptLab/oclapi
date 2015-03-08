from mappings.importer import MappingsImporter
from oclapi.management.commands import ImportCommand

__author__ = 'misternando'


class Command(ImportCommand):
    help = 'Import mappings from a JSON file into a source'

    def do_import(self, user, source, input_file, options):
        importer = MappingsImporter(source, input_file, self.stdout, self.stderr, user)
        importer.import_mappings(**options)
