import json
from ocldev.oclfleximporter import OclFlexImporter

from users.models import UserProfile

class ImportResults:
    def __init__(self, importer):
        self.json = importer.import_results.to_json()
        self.detailed_summary = importer.import_results.get_detailed_summary()
        self.report = importer.import_results.display_report()


class BulkImport:
    def __init__(self):
        pass

    def run_import(self, to_import, username, update_if_exists):
        input_list = []
        for line in to_import.splitlines():
            input_list.append(json.loads(line))

        profile = UserProfile.objects.get(mnemonic=username)
        importer = OclFlexImporter(input_list=input_list, api_url_root='http://api.openconceptlab.org:8000',
                                   api_token=profile.user.auth_token.key, do_update_if_exists=update_if_exists)
        importer.process()

        return ImportResults(importer)
