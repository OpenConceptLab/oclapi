""" import_concepts_to_source - Command to import JSON lines concept file into OCL """
from concepts.importer import ConceptsImporter, ValidationLogger
from oclapi.management.commands import ImportCommand


class Command(ImportCommand):
    """ Command to import JSON lines concept file into OCL """
    help = 'Import concepts from a JSON file into a source'

    def do_import(self, user, source, input_file, options):
        """ Performs the import of JSON lines concept file into OCL """
        validation_logger = None
        output_file_name = options.get('error_output_file', False)
        if output_file_name:
            validation_logger = ValidationLogger(output_file_name=output_file_name)
        importer = ConceptsImporter(source, input_file, user, self.stdout, self.stderr, validation_logger=validation_logger)
        importer.import_concepts(**options)