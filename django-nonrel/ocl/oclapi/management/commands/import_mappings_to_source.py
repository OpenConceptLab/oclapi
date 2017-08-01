""" import_mappings_to_source - Command to import JSON lines mapping file into OCL """
from mappings.importer import MappingsImporter
from oclapi.management.commands import ImportCommand

__author__ = 'misternando,paynejd'


class Command(ImportCommand):
    """ Command to import JSON lines mapping file into OCL """
    help = 'Import mappings from a JSON file into a source'

    def do_import(self, user, source, input_file, options):
        """ Perform the mapping import """
        importer = MappingsImporter(source, input_file, self.stdout, self.stderr, user)
        importer.import_mappings(**options)
