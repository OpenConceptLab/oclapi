""" import_concepts_to_source - Command to import JSON lines concept file into OCL """
from concepts.importer import ConceptsImporter
from oclapi.management.commands import ImportCommand

class Command(ImportCommand):
    """ Command to import JSON lines concept file into OCL """
    help = 'Import concepts from a JSON file into a source'

    def do_import(self, user, source, input_file, options):
        """ Performs the import of JSON lines concept file into OCL """
        importer = ConceptsImporter(source, input_file, user, self.stdout, self.stderr)
        importer.import_concepts(**options)